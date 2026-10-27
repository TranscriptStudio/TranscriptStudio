# services/traitements/journal.py
"""
Log des opérations de l'étude (P15.4).

Contrat : CONTRAT_FORMAT_ETUDE_V2.md §11 ; comportement :
SPEC_MOTEUR_P15_V2.md §5 (décision David B1bis, remplace
l'ancien « journal de passe »).

Fichier dédié associé à l'étude :
``traitements/journal_operations.json``.

- journalise **toutes les opérations du process** :
  passes complètes, reformulations par bloc, éditions
  manuelles, validations/dévalidations, fusions,
  erreurs API, annulations (résumés et synthèses en
  P17) ;
- **append-only** : aucune entrée n'est jamais
  effacée ni réécrite ; fichier unique pour toute
  l'étude ;
- **écrit à chaque opération** (pas seulement en
  fin de passe) : le log survit à un crash ;
- **document d'audit et d'affichage uniquement** :
  jamais consommé par le moteur ni les
  traitements ; l'affichage in-app (icône Log,
  spec UI §8) le lit en lecture seule.

Chaque entrée porte : ``horodatage``, ``type``,
``fid`` (null si périmètre réunion/passe),
``reunion``, ``modele``, ``version`` produite le
cas échéant, ``resultat`` (« succes » / « erreur »
+ message) et ``stats`` pour un appel LLM.
"""

import json
from pathlib import Path

from services.timecodes import horodatage_iso


JOURNAL_VERSION = 1

FICHIER_JOURNAL = "journal_operations.json"

#
# Types d'opérations journalisés (contrat §11).
#

TYPE_PASSE_COMPLETE = "passe_complete"
TYPE_REFORMULATION_BLOC = "reformulation_bloc"
TYPE_EDITION_MANUELLE = "edition_manuelle"
TYPE_VALIDATION = "validation"
TYPE_DEVALIDATION = "devalidation"
TYPE_FUSION_BLOCS = "fusion_blocs"
TYPE_ERREUR_API = "erreur_api"
TYPE_ANNULATION_PASSE = "annulation_passe"
TYPE_RESUME = "resume"
TYPE_SYNTHESE = "synthese"

TYPES_ENTRUES = (
    TYPE_PASSE_COMPLETE,
    TYPE_REFORMULATION_BLOC,
    TYPE_EDITION_MANUELLE,
    TYPE_VALIDATION,
    TYPE_DEVALIDATION,
    TYPE_FUSION_BLOCS,
    TYPE_ERREUR_API,
    TYPE_ANNULATION_PASSE,
    TYPE_RESUME,
    TYPE_SYNTHESE,
)

RESULTAT_SUCCES = "succes"
RESULTAT_ERREUR = "erreur"


class JournalError(Exception):
    """
    Erreur de format ou d'écriture du journal.
    """

    pass


class JournalEtude:
    """
    Log des opérations d'une étude, append-only,
    écrit à chaque opération.

    Le journal est indépendant de la sauvegarde de
    l'étude : chaque opération écrit son entrée sur
    le disque immédiatement (survie aux crashes).
    """

    def __init__(self, chemin=None):
        self.chemin = (
            Path(chemin) if chemin else None
        )
        self.entrees = []

        if self.chemin is not None:
            self.charger()

    #
    # Chargement / écriture.
    #

    def charger(self) -> None:
        """
        Charge le journal existant ; absent, le
        journal démarre vide (études antérieures à
        P15.4 — l'entrée suivante créera le
        fichier).
        """

        if self.chemin is None:
            return

        if not self.chemin.exists():
            self.entrees = []
            return

        try:

            with open(
                self.chemin,
                "r",
                encoding="utf-8"
            ) as fichier:
                data = json.load(fichier)

        except json.JSONDecodeError as e:
            raise JournalError(
                f"Journal illisible ({self.chemin}) : {e}"
            )

        self._valider(data)

        self.entrees = list(data.get("entrees", []))

    def initialiser(self) -> None:
        """
        Crée le fichier journal (vide) s'il n'existe
        pas encore — à la création d'une étude.

        Ne touche jamais à un journal existant
        (append-only).
        """

        if self.chemin is None:
            return

        if self.chemin.exists():
            return

        self._ecrire()

    def _ecrire(self) -> None:
        """
        Écrit le journal complet sur le disque.

        Sémantique append-only : le fichier est
        réécrit avec l'intégralité des entrées —
        aucune entrée existante n'est jamais
        modifiée ni retirée.
        """

        if self.chemin is None:
            return

        self.chemin.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        data = {
            "journal_version": JOURNAL_VERSION,
            "entrees": self.entrees,
        }

        with open(
            self.chemin,
            "w",
            encoding="utf-8"
        ) as fichier:
            json.dump(
                data,
                fichier,
                ensure_ascii=False,
                indent=2
            )

    def _valider(self, data) -> None:
        """
        Cohérence minimale du fichier journal.
        """

        if not isinstance(data, dict):
            raise JournalError(
                "Journal : objet JSON attendu"
            )

        entrees = data.get("entrees")

        if not isinstance(entrees, list):
            raise JournalError(
                "Journal : liste d'entrées attendue"
            )

        for index, entree in enumerate(entrees):

            if not isinstance(entree, dict):
                raise JournalError(
                    f"entrees[{index}] : objet attendu"
                )

            if entree.get("type") not in TYPES_ENTRUES:
                raise JournalError(
                    f"entrees[{index}] : type inconnu "
                    f"{entree.get('type')!r}"
                )

            if not entree.get("horodatage"):
                raise JournalError(
                    f"entrees[{index}] : horodatage requis"
                )

    #
    # Ajout d'entrées (une par opération, avant
    # retour à l'UI — règle d'invariance 4 de la
    # spec moteur).
    #

    def ajouter(
        self,
        type_operation: str,
        fid=None,
        reunion: str = None,
        modele: str = None,
        version: int = None,
        resultat: str = RESULTAT_SUCCES,
        message: str = None,
        stats: dict = None,
        extras: dict = None
    ) -> dict:
        """
        Consigne une opération : ajoute l'entrée et
        l'écrit sur le disque immédiatement.

        Retourne l'entrée créée.
        """

        if type_operation not in TYPES_ENTRUES:
            raise JournalError(
                f"Type d'opération inconnu : "
                f"{type_operation!r}"
            )

        entree = {
            "horodatage": horodatage_iso(),
            "type": type_operation,
            "fid": fid,
            "reunion": reunion,
            "modele": modele,
            "version": version,
            "resultat": resultat,
        }

        if message is not None:
            entree["message"] = message

        entree["stats"] = stats

        if extras:

            for cle, valeur in extras.items():

                if cle not in entree:
                    entree[cle] = valeur

        self.entrees.append(entree)

        self._ecrire()

        return entree

    #
    # Lecture (affichage uniquement).
    #

    def nb_entrees(self) -> int:

        return len(self.entrees)

    def dernieres(self, nombre: int = None) -> list:
        """
        Entrées en ordre chronologique, éventuellement
        limitées aux N dernières — pour l'affichage
        en lecture seule.
        """

        if nombre is None:
            return list(self.entrees)

        return list(self.entrees[-nombre:])
