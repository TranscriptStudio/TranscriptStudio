# services/preprocessing_journal.py
"""
Journal des opérations de prétraitement audio (P14.2).

Contrat : CONTRAT_FORMAT_ETUDE_V2.md §11 et
FEUILLE_DE_ROUTE_V2.md §3.1 (interventions uniques longues).

Le journal est un fichier additionnel du projet v1,
``journal_operations.json``, écrit dans le dossier du
projet au moment du prétraitement :

- additif et non destructif : le format v1 n'est pas
  modifié ;
- un nouveau journal remplace l'ancien à chaque
  re-prétraitement (pas de composition) ;
- jamais supprimé par l'étude ; sa présence est
  optionnelle (projets v1 antérieurs).

L'enchaînement réel reflète le pipeline
(services/audio_processing_pipeline.py) : découpe,
puis suppression des silences, puis accélération.

Règles de composition (feuille de route §3.1) :
- l'accélération s'applique aux positions
  post-suppression (les silences n'existent plus
  dans l'audio accéléré) ;
- les silences supprimés ne sont pas accélérés ;
- les positions et durées originales des silences
  restent exprimées dans le référentiel du discours
  original (pré-découpe) ; le buffer conservé de
  chaque côté du silence est consigné pour ne pas
  fausser la mesure des pauses réelles (P14.4).

Ce module expose deux fonctions de conversion pures,
testées unitairement :
- ``position_originale_vers_traitee`` ;
- ``position_traitee_vers_originale``.

Sémantique des frontières (documentée, arbitrage à
l'atelier si besoin) :
- une position située dans la partie supprimée d'un
  silence se projette sur le début de la partie
  supprimée (fin de l'audio conservé avant la coupe) ;
- après suppression, la fin du silence (début de
  l'audio conservé après la coupe) et le début de la
  partie supprimée sont adjacents : ils partagent la
  même position dans l'audio traité, et la conversion
  retour ramène cette position au début de la partie
  supprimée.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from services.timecodes import (
    formater_timecode,
    lire_timecode,
)


FICHIER_JOURNAL = "journal_operations.json"

TYPE_DECOUPE = "decoupe"
TYPE_SILENCE_SUPPRIME = "silence_supprime"
TYPE_ACCELERATION = "acceleration"

_EPSILON = 1e-9


class JournalError(Exception):
    """
    Erreur de format ou de manipulation du journal
    des opérations.
    """

    pass


@dataclass
class JournalOperations:
    """
    Liste ordonnée des opérations de prétraitement,
    reflétant l'enchaînement réel du pipeline.
    """

    journal_version: int = 1
    horodatage: str = ""
    operations: list = field(default_factory=list)

    def to_dict(self) -> dict:

        return {
            "journal_version": self.journal_version,
            "horodatage": self.horodatage,
            "operations": list(self.operations),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JournalOperations":

        valider_journal(data)

        return cls(
            journal_version=data["journal_version"],
            horodatage=data["horodatage"],
            operations=list(data["operations"]),
        )


def valider_journal(data: dict) -> None:
    """
    Valide la structure d'un journal brut. Lève
    JournalError en cas de violation.
    """

    if not isinstance(data, dict):
        raise JournalError(
            "Journal : objet JSON attendu"
        )

    if data.get("journal_version") != 1:
        raise JournalError(
            "Journal : journal_version != 1 non "
            "supportée"
        )

    if not isinstance(data.get("horodatage"), str):
        raise JournalError(
            "Journal : horodatage requis"
        )

    operations = data.get("operations")

    if not isinstance(operations, list):
        raise JournalError(
            "Journal : liste d'opérations attendue"
        )

    for index, operation in enumerate(operations):

        prefixe = f"opérations[{index}]"

        if not isinstance(operation, dict):
            raise JournalError(
                f"{prefixe} : objet attendu"
            )

        type_operation = operation.get("type")

        if type_operation == TYPE_DECOUPE:

            positions = operation.get("positions")

            if (
                not isinstance(positions, list)
                or len(positions) != 2
            ):
                raise JournalError(
                    f"{prefixe} : découpe = deux "
                    "positions attendues"
                )

            for position in positions:
                _lire_timecode_or_erreur(
                    position,
                    f"{prefixe}.positions"
                )

        elif type_operation == TYPE_SILENCE_SUPPRIME:

            for cle in ("position", "duree_originale"):
                _lire_timecode_or_erreur(
                    operation.get(cle),
                    f"{prefixe}.{cle}"
                )

            buffer = operation.get("buffer", 0.0)

            try:
                buffer = _lire_timecode_or_nombre(
                    buffer
                )
            except JournalError:
                raise JournalError(
                    f"{prefixe}.buffer : timecode ou "
                    "nombre de secondes attendu"
                )

            duree = lire_timecode(
                operation["duree_originale"]
            )

            if buffer < 0 or 2 * buffer >= duree:
                raise JournalError(
                    f"{prefixe} : le buffer "
                    f"({buffer}s) couvre toute la "
                    f"durée du silence ({duree}s) : "
                    "aucune partie n'est supprimée"
                )

        elif type_operation == TYPE_ACCELERATION:

            facteur = operation.get("facteur")

            if (
                not isinstance(facteur, (int, float))
                or facteur <= 1.0
            ):
                raise JournalError(
                    f"{prefixe} : facteur "
                    "d'accélération > 1 attendu"
                )

        else:
            raise JournalError(
                f"{prefixe} : type inconnu "
                f"{type_operation!r}"
            )


def _lire_timecode_or_erreur(valeur, contexte: str):
    """
    Lit un timecode ou lève une JournalError lisible.
    """

    try:
        return lire_timecode(valeur)
    except (ValueError, TypeError):
        raise JournalError(
            f"{contexte} : timecode invalide "
            f"({valeur!r})"
        )


def _lire_timecode_or_nombre(valeur):
    """
    Lit un timecode ("HH:MM:SS.mmm") ou un nombre
    de secondes.
    """

    if isinstance(valeur, (int, float)):
        return float(valeur)

    return lire_timecode(valeur)


def ajouter_decoupe(
    journal: JournalOperations,
    debut: float,
    fin: float
) -> None:
    """
    Ajoute l'opération de découpe début/fin
    (positions dans le discours original).
    """

    journal.operations.append({
        "type": TYPE_DECOUPE,
        "positions": [
            formater_timecode(debut),
            formater_timecode(fin),
        ],
    })


def ajouter_silence_supprime(
    journal: JournalOperations,
    position: float,
    duree_originale: float,
    buffer: float = 0.0
) -> None:
    """
    Ajoute l'opération de suppression d'un silence.

    ``position`` : début du silence détecté, dans le
    référentiel du discours original (pré-découpe).
    ``duree_originale`` : durée du silence détecté.
    ``buffer`` : durée conservée de chaque côté du
    silence dans l'audio traité.
    """

    journal.operations.append({
        "type": TYPE_SILENCE_SUPPRIME,
        "position": formater_timecode(position),
        "duree_originale": formater_timecode(
            duree_originale
        ),
        "buffer": buffer,
    })


def ajouter_acceleration(
    journal: JournalOperations,
    facteur: float
) -> None:
    """
    Ajoute l'opération d'accélération (facteur > 1,
    appliqué aux positions post-suppression).
    """

    journal.operations.append({
        "type": TYPE_ACCELERATION,
        "facteur": facteur,
    })


def enregistrer_journal(
    journal: JournalOperations,
    dossier_projet
) -> Path:
    """
    Écrit le journal dans le dossier projet v1
    (remplace l'ancien : pas de composition).
    """

    chemin = (
        Path(dossier_projet) / FICHIER_JOURNAL
    )

    with open(
        chemin,
        "w",
        encoding="utf-8"
    ) as fichier:
        json.dump(
            journal.to_dict(),
            fichier,
            ensure_ascii=False,
            indent=2
        )

    return chemin


def charger_journal(dossier_projet):
    """
    Charge le journal d'un dossier projet v1.

    Retourne None si le journal est absent (projets
    v1 antérieurs) : sa présence est optionnelle.
    """

    chemin = (
        Path(dossier_projet) / FICHIER_JOURNAL
    )

    if not chemin.exists():
        return None

    with open(
        chemin,
        "r",
        encoding="utf-8"
    ) as fichier:
        data = json.load(fichier)

    return JournalOperations.from_dict(data)


def _analyser_journal(journal: JournalOperations):
    """
    Décompose le journal en paramètres de conversion.

    Retourne (t0, t1, silences, facteur) :
    - t0, t1 : bornes conservées par la découpe dans
      le référentiel original (t1=None si la découpe
      ne fixe pas de fin) ;
    - silences : liste triée de tuples
      (debut_suppression, fin_suppression,
      duree_originale, buffer) — la partie réellement
      supprimée de chaque silence et sa durée
      originale complète, dans le référentiel
      original ;
    - facteur : facteur d'accélération (1 si absent).
    """

    t0 = 0.0
    t1 = None
    silences = []
    facteur = 1.0

    for operation in journal.operations:

        type_operation = operation["type"]

        if type_operation == TYPE_DECOUPE:

            debut, fin = operation["positions"]

            t0 = lire_timecode(debut)
            t1 = lire_timecode(fin)

        elif type_operation == TYPE_SILENCE_SUPPRIME:

            position = lire_timecode(
                operation["position"]
            )

            duree = lire_timecode(
                operation["duree_originale"]
            )

            buffer = _lire_timecode_or_nombre(
                operation.get("buffer", 0.0)
            )

            silences.append(
                (
                    position + buffer,
                    position + duree - buffer,
                    duree,
                    buffer,
                )
            )

        elif type_operation == TYPE_ACCELERATION:

            facteur = float(operation["facteur"])

    silences.sort()

    return t0, t1, silences, facteur


def position_originale_vers_traitee(
    journal: JournalOperations,
    position: float
) -> float:
    """
    Convertit une position du discours original vers
    l'audio traité (secondes).

    Composition : découpe, puis suppression des
    silences, puis accélération. Le calcul se fait
    dans le référentiel original ; t0 et le cumul
    supprimé ne sont retranchés qu'à la fin.

    Une position antérieure à la découpe vaut 0 ;
    une position postérieure à la fin conservée est
    ramenée à la fin ; une position située dans la
    partie supprimée d'un silence se projette sur la
    fin de l'audio conservé qui la précède.
    """

    t0, t1, silences, facteur = _analyser_journal(
        journal
    )

    if position < t0:
        return 0.0

    if t1 is not None and position > t1:
        position = t1

    cumul_supprime = 0.0

    for (
        debut_suppression,
        fin_suppression,
        _duree,
        _buffer
    ) in silences:

        if position <= debut_suppression:
            break

        if position < fin_suppression:

            #
            # Position dans la partie supprimée :
            # projection sur le début de la coupe
            # (fin de l'audio conservé précédent).
            #

            position = debut_suppression
            break

        cumul_supprime += (
            fin_suppression - debut_suppression
        )

    return (
        position - t0 - cumul_supprime
    ) / facteur


def position_traitee_vers_originale(
    journal: JournalOperations,
    position: float
) -> float:
    """
    Convertit une position de l'audio traité vers le
    discours original (secondes).

    Inverse de ``position_originale_vers_traitee`` :
    l'accélération est défaite, puis les silences
    supprimés sont réinsérés, puis la découpe est
    défaites.

    Une position située exactement à une frontière
    de silence se ramène au début de la partie
    supprimée (voir sémantique des frontières en
    tête de module).
    """

    t0, t1, silences, facteur = _analyser_journal(
        journal
    )

    #
    # Référentiel courant : audio découpé, silences
    # non réinsérés (positions de l'audio traité
    # avant accélération).
    #

    position = position * facteur

    cumul_supprime = 0.0

    for (
        debut_suppression,
        fin_suppression,
        _duree,
        _buffer
    ) in silences:

        debut_apres_suppression = (
            debut_suppression - t0 - cumul_supprime
        )

        if (
            position
            < debut_apres_suppression - _EPSILON
        ):
            break

        if (
            abs(
                position
                - debut_apres_suppression
            ) <= _EPSILON
        ):
            #
            # Frontière exacte : conservatrice,
            # on ne réinsère pas.
            #

            break

        cumul_supprime += (
            fin_suppression - debut_suppression
        )

        position += (
            fin_suppression - debut_suppression
        )

    return position + t0


def duree_originale_pause(
    journal: JournalOperations,
    position_traitee: float,
    seuil: float = 1.0
):
    """
    Durée originale de la pause (silence supprimé)
    située à une position de l'audio traité, si elle
    atteint le seuil ; None sinon.

    Sert au sous-découpage des monologues (P14.4) :
    la coupe se situe dans le silence résiduel que
    le buffer a conservé dans l'audio traité (chaque
    côté du buffer, réduit par l'accélération) — la
    position est donc acceptée dans cette marge, et
    la durée retournée est celle du silence originel
    complet (le buffer est déduit pour ne pas fausser
    la mesure de la pause réelle).
    """

    t0, t1, silences, facteur = _analyser_journal(
        journal
    )

    position = position_traitee * facteur

    cumul_supprime = 0.0

    for (
        debut_suppression,
        fin_suppression,
        duree_originale,
        buffer
    ) in silences:

        debut_apres_suppression = (
            debut_suppression - t0 - cumul_supprime
        )

        marge = buffer / facteur

        if (
            position
            < debut_apres_suppression - marge
            - _EPSILON
        ):
            return None

        if (
            position
            <= debut_apres_suppression + marge
            + _EPSILON
        ):

            if duree_originale >= seuil:
                return duree_originale

            return None

        cumul_supprime += (
            fin_suppression - debut_suppression
        )

        position += (
            fin_suppression - debut_suppression
        )

    return None
