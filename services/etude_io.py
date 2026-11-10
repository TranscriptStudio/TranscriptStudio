# services/etude_io.py
"""
Lecture, écriture et manipulation d'une étude v2 (P14.1,
refondue P18.7).

P18.7 — stockage des traitements au niveau RÉUNION :

- le **tier réunion** vit dans le projet v1
  (``transcriptstudio\\``, services/tier_reunion.py) :
  reunion.json, blocs/journal-fid.json + decoupage.json,
  traitements/reformulation/<FID>.json + resume.json +
  journal_operations.json, parametres/parametres.json ;
- **identité de bloc = (réunion, FID)** : le registre FID
  est PAR RÉUNION dans le tier ; le registre global d'étude
  est abrogé pour les nouvelles données (les études v1 sont
  migrées à l'ouverture, P18.7f) ;
- l'**étude v2** ne garde que etude.json, reunions/<nom>.json
  (titre_1, chemins ; resume_valide a migré vers le tier),
  synthese/, parametres/ (surcharges synthèse uniquement) et
  journal_etude.json — blocs\\ et traitements\\ disparaissent
  du dossier étude ;
- **aucune écriture en retour** : sauvegarder_etude n'écrit
  JAMAIS dans les tiers ; seules les opérations sur les
  traitements d'une réunion y écrivent (elles sauvegardent
  le tier explicitement) ;
- toute divergence etudes[] du tier vs ordre_reunions de
  l'étude est signalée à l'ouverture (``divergences``),
  jamais auto-corrigée.

Règles de fond conservées :
- ouvrir ou manipuler une étude ne modifie jamais un projet
  v1 référencé, HORS la création additive de son tier
  ``transcriptstudio\\`` quand il n'existe pas encore ;
- un couple (réunion, FID), une fois attribué, désigne pour
  toujours le même discours ; les versions ne s'écrasent
  pas ;
- le détachement d'une réunion est non destructif : la
  réunion garde tout son travail (son tier reste dans le
  projet v1) ;
- les chemins se résolvent par ordre relatif, puis absolu,
  puis relocalisation guidée.

Un projet introuvable n'empêche pas l'ouverture : l'étude
s'ouvre en mode dégradé (réunions joignables uniquement).
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

from models.etude import (
    DecoupageReunion,
    EntreeFID,
    Etude,
    ETUDE_FORMAT_VERSION,
    ETUDE_FORMAT_VERSION_V1,
    ParametresEtude,
    RegistreFID,
    ResultatReformulation,
    ResultatResume,
    ReunionEtude,
    SyntheseEtude,
    Validation,
    VersionReformulation,
    VersionResume,
    VersionSynthese,
    normaliser_nom_fichier,
)
from services.etude_schema import (
    EtudeFormatError,
    valider_decoupage,
    valider_etude,
    valider_parametres,
    valider_parametres_synthese_seule,
    valider_registre_fid,
    valider_reformulation,
    valider_reunion,
    valider_resume,
    valider_synthese,
)
from services.prompts import (
    USAGE_FUSION,
    USAGE_REFORMULATION,
    USAGE_RESUME,
    prompt_initial,
)
from services.timecodes import horodatage_iso
from services.controle_qualite import (
    INTERDITS_STYLISTIQUES_DEFAUT,
)
from services.traitements.journal import (
    FICHIER_JOURNAL,
    JournalEtude,
    RESULTAT_SUCCES,
    TYPE_DEVALIDATION,
    TYPE_EDITION_MANUELLE,
    TYPE_REFORMULATION_BLOC,
    TYPE_RESUME,
    TYPE_SYNTHESE,
    TYPE_VALIDATION,
)
from services.tier_reunion import (
    DOSSIER_TIER,
    FICHIER_REUNION as FICHIER_REUNION_TIER,
    TierReunion,
    creer_tier,
    ouvrir_tier,
    sauvegarder_tier,
    tier_existe,
)


FICHIER_ETUDE = "etude.json"

DOSSIER_REUNIONS = "reunions"
DOSSIER_BLOCS = "blocs"                    # v1 uniquement
DOSSIER_DECOUPAGE = "decoupage"            # v1 uniquement
DOSSIER_TRAITEMENTS = "traitements"        # v1 uniquement
DOSSIER_REFORMULATION = "reformulation"
DOSSIER_RESUME = "resume"                  # v1 uniquement (dossier)
DOSSIER_SYNTHESE = "synthese"
DOSSIER_PARAMETRES = "parametres"
DOSSIER_SAUVEGARDES = "sauvegardes"        # migration §11

FICHIER_REGISTRE_FID = "journal-fid.json"
FICHIER_SYNTHESE = "synthese.json"
FICHIER_PARAMETRES = "parametres.json"
FICHIER_JOURNAL_ETUDE = "journal_etude.json"   # v2 (niveau étude)


class EtudeError(Exception):
    """
    Erreur de manipulation d'une étude (opération
    impossible, réunion inconnue, FID inexistant...).
    """

    pass


def horodatage_courant() -> str:
    """
    Horodatage ISO local ``AAAA-MM-JJTHH:MM:SS``.
    """

    return horodatage_iso()


def normaliser_sauts_paragraphe(texte: str) -> str:
    """
    Normalise un texte stocké : un seul retour à la
    ligne par saut de paragraphe (contrat §2).

    Les retours Windows sont ramenés à des retours simples,
    les successions de lignes vides sont réduites à un seul
    saut de paragraphe.
    """

    if texte is None:
        return texte

    texte = texte.replace("\r\n", "\n")
    texte = texte.replace("\r", "\n")

    texte = re.sub(r"\n{2,}", "\n", texte)

    return texte.strip("\n").strip()


def _normaliser_chemin(chemin: str) -> str:
    """
    Normalise un chemin pour stockage JSON : séparateurs /.
    """

    if chemin is None:
        return None

    return str(chemin).replace("\\", "/")


def _chemin_relatif(
    dossier_etude: Path,
    cible: Path
) -> str:
    """
    Chemin relatif du dossier étude vers la cible,
    normalisé pour JSON.
    """

    relatif = os.path.relpath(
        str(cible.resolve()),
        str(dossier_etude.resolve())
    )

    return _normaliser_chemin(relatif)


def _ecrire_json(chemin: Path, data: dict) -> None:
    """
    Écrit un fichier JSON de l'étude (UTF-8).
    """

    chemin.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        chemin,
        "w",
        encoding="utf-8"
    ) as fichier:
        json.dump(
            data,
            fichier,
            ensure_ascii=False,
            indent=2
        )


def _lire_json(chemin: Path) -> dict:
    """
    Lit un fichier JSON de l'étude (UTF-8).
    """

    with open(
        chemin,
        "r",
        encoding="utf-8"
    ) as fichier:
        return json.load(fichier)


def parametres_par_defaut(
    temperature_reformulation: float = 0.3,
    temperature_resume: float = 0.2,
    dossier_prompts=None
) -> ParametresEtude:
    """
    Paramètres initiaux (contrat §10) : prompts v2
    intégrés comme valeurs actives — depuis la
    BIBLIOTHÈQUE depuis P16-ter (fichier
    prompts/<usage>.md du dossier de paramétrage s'il
    existe, défaut embarqué sinon) — températures par
    défaut venant des réglages de l'app (décision C2 :
    reformulation 0.3, résumé 0.2), aucun secret
    (CredentialStore v1).

    En v2 (P18.7e), ces paramètres sont ceux DU TIER de
    chaque réunion ; l'étude ne garde que la surcharge
    de synthèse.
    """

    return ParametresEtude(
        reformulation={
            "prompt": prompt_initial(
                USAGE_REFORMULATION,
                dossier_prompts
            ),
            "modele": "mistral-large-latest",
            "temperature": temperature_reformulation,
            "fenetre_glissante_tokens": 2000,
            # Cases de contexte du bloc (feuille de
            # route §3.1 : la synthèse d'étude sert
            # aux blocs qui le cochent) — P17.2.
            "contexte": {
                "fenetre_glissante": True,
                "synthese_etude": True,
            },
        },
        resume={
            "prompt": prompt_initial(
                USAGE_RESUME,
                dossier_prompts
            ),
            "modele": "mistral-large-latest",
            "temperature": temperature_resume,
            "longueur_cible_mots": [650, 700],
            "source_defaut": "reformulations_valides",
        },
        synthese={
            "tokens_max": 1500,
            "modele": "mistral-small-latest",
        },
        controle_qualite={
            "lexique_emphase": [
                "puissamment",
                "profondément",
                "véritablement",
            ],
            # Interdits stylistiques (feuille de route
            # §5.3, P16.4) : liste éditable dans les
            # paramètres.
            "interdits_stylistiques": (
                INTERDITS_STYLISTIQUES_DEFAUT
            ),
        },
        llm={
            "fournisseurs": [
                {
                    "nom": "mistral",
                    "url": "https://api.mistral.ai/v1",
                    "cle_ref": "credential_store",
                },
            ],
        },
        # P18.5 (spec BIBLE_JND_V2 §3) : version de
        # Bible retenue, défaut darbyR (Darby
        # révisée, décision David 2026-10-28).
        bible={
            "version": "darbyR",
        },
        # P19.4-bis (ARBITRAGE_PROMPT_FUSION) :
        # copie locale du prompt de fusion (bibliothèque
        # prompts/fusion.md, à défaut embarqué).
        fusion={
            "prompt": prompt_initial(
                USAGE_FUSION,
                dossier_prompts
            ),
        },
    )


class _VueEntrees(dict):
    """
    Vue agrégée des entrées de registre de plusieurs
    réunions (lecture seule) : ``values()`` retourne
    TOUTES les entrées (les FID peuvent se chevaucher
    entre réunions). P20 fin (ARBITRAGE_P18_7_ECARTS, écart 5) :
    la résolution par FID nu est RETIRÉE — identité de bloc
    = couple (réunion, FID) ; utiliser ``registre_de(nom)``.
    """

    def __init__(self):
        super().__init__()
        self._toutes = []

    def ajouter_tier(self, registre: RegistreFID) -> None:
        for fid, entree in registre.entrees.items():
            self._toutes.append(entree)
            dict.__setitem__(
                self,
                (entree.reunion, fid),
                entree
            )

    def values(self):
        return list(self._toutes)




class _VueReformulations(dict):
    """
    Reformulations agrégées, indexées par le couple
    (réunion, FID).

    P20 fin (ARBITRAGE_P18_7_ECARTS, écart 5) : la
    compatibilité de lecture par FID NU est RETIRÉE —
    seules les clés (réunion, FID) résolvent ; utiliser
    ``reformulation_de(nom, fid)``.
    """

    def _resoudre(self, cle):
        if not isinstance(cle, tuple):
            raise EtudeError(
                "Clé (réunion, FID) attendue — le FID nu "
                "n'est plus accepté (P20 fin) : utiliser "
                "reformulation_de(nom, fid)"
            )
        return cle

    def get(self, cle, default=None):
        return dict.get(self, self._resoudre(cle), default)

    def __getitem__(self, cle):
        return dict.__getitem__(self, self._resoudre(cle))

    def __contains__(self, cle):
        return dict.__contains__(self, self._resoudre(cle))


class EtudeOuverte:
    """
    Une étude chargée en mémoire, avec l'état de
    résolution de ses réunions.

    P18.7 : les traitements de chaque réunion vivent dans
    son **tier** (``tiers[nom]``, stocké dans le projet v1) ;
    l'identité de bloc est le couple **(réunion, FID)**.

    ``reunions_introuvables`` liste les réunions dont le
    projet v1 est introuvable (mode dégradé : elles
    n'empêchent pas l'ouverture des autres).

    ``divergences`` : signalements à l'ouverture — toute
    divergence entre etudes[] du tier et ordre_reunions de
    l'étude (P18.7d), jamais auto-corrigée.

    ``mode_autonome`` : étude synthétique portée par un
    projet v1 seul (réunion autonome) — la sauvegarde
    n'écrit alors que le tier.
    """

    def __init__(self):

        self.dossier: Path = None
        self.etude: Etude = None
        self.parametres: ParametresEtude = None
        self.synthese: SyntheseEtude = None

        self.reunions: dict = {}

        # P18.7 : tier de chaque réunion joignable.
        self.tiers: dict = {}

        # Log des opérations de NIVEAU ÉTUDE (synthèse,
        # rattachements...) : journal_etude.json en v2,
        # traitements/journal_operations.json en v1.
        # Le journal de chaque réunion vit dans son tier.
        self.journal = None

        self.reunions_introuvables: list = []

        # Chemin du projet v1 résolu pour chaque réunion
        # joignable (None sinon).
        self.chemins_resolus: dict = {}

        # Signalements etudes[] vs ordre_reunions (P18.7d).
        self.divergences: list = []

        # Réunion autonome (pas de dossier étude).
        self.mode_autonome: bool = False

        # Registre global : études v1 uniquement (en v2,
        # abrogé — les registres sont par réunion, dans les
        # tiers).
        self._registre_v1: RegistreFID = None

    #
    # Accès par réunion — identité de bloc = (réunion, FID).
    #

    def est_v2(self) -> bool:
        return (
            self.etude is not None
            and self.etude.etude_format_version == 2
        )

    def tier_de(self, nom: str) -> TierReunion:
        """
        Le tier de la réunion (stocké dans son projet v1).
        """

        tier = self.tiers.get(nom)

        if tier is None:
            raise EtudeError(
                f"Aucun tier pour la réunion {nom} "
                "(projet v1 introuvable ?)"
            )

        return tier

    def registre_de(self, nom: str) -> RegistreFID:
        """
        Le registre FID DE LA RÉUNION (P18.7b).
        """

        if self.est_v2():
            return self.tier_de(nom).registre

        return self._registre_v1

    def decoupage_de(self, nom: str):
        return self.tier_de(nom).decoupage

    def reformulation_de(self, nom: str, fid: int):
        return self.tier_de(nom).reformulations.get(fid)

    def resume_de(self, nom: str):
        return self.tier_de(nom).resume

    @property
    def registre(self) -> RegistreFID:
        """
        Registre global — études v1 uniquement. En v2 il
        est ABROGÉ pour les nouvelles données : utiliser
        ``registre_de(nom)`` (registre par réunion, dans
        le tier).

        En v2, cette propriété retourne une VUE AGRÉGÉE en
        lecture seule (fusion des registres des tiers) pour
        compatibilité ; les écritures passent par
        ``attribuer_fid`` / ``marquer_fid_inactif`` /
        ``reactiver_fid``.
        """

        if not self.est_v2():
            return self._registre_v1

        if len(self.tiers) == 1:
            return next(iter(self.tiers.values())).registre

        entrees = _VueEntrees()

        for tier in self.tiers.values():
            entrees.ajouter_tier(tier.registre)

        prochain = max(
            (t.registre.prochain_fid for t in self.tiers.values()),
            default=1
        )

        return RegistreFID(
            prochain_fid=prochain,
            entrees=entrees
        )

    #
    # Vues agrégées (lecture seule) — reformulations
    # indexées par le couple (réunion, FID). Un FID nu
    # résout vers l'unique couple le portant quand il
    # n'y a pas d'ambiguïté (compatibilité de lecture).
    #

    @property
    def decoupages(self) -> dict:
        return {
            nom: tier.decoupage
            for nom, tier in self.tiers.items()
            if tier.decoupage is not None
        }

    @property
    def reformulations(self) -> dict:
        return _VueReformulations({
            (nom, fid): resultat
            for nom, tier in self.tiers.items()
            for fid, resultat in tier.reformulations.items()
        })

    @property
    def resumes(self) -> dict:
        return {
            nom: tier.resume
            for nom, tier in self.tiers.items()
            if tier.resume is not None
        }

    def reunion_joignable(self, nom: str) -> bool:
        """
        La réunion est-elle joignable (projet v1
        résolu) ?
        """

        return (
            nom in self.chemins_resolus
            and self.chemins_resolus[nom] is not None
        )

    def journal_traitement(self, nom: str) -> JournalEtude:
        """
        Le journal des opérations de traitement de la
        réunion : celui DU TIER en v2 (chaque opération
        sur les traitements d'une réunion y est consignée),
        le journal d'étude en v1.
        """

        if self.est_v2():
            return self.tier_de(nom).journal

        return self.journal

    def parametres_traitement_de(self, nom: str) -> ParametresEtude:
        """
        P18.7e : les paramètres utilisés par TOUTE opération
        sur les traitements d'une réunion, où qu'elle soit
        lancée, sont ceux DU TIER de la réunion. En v1
        (avant migration), ceux de l'étude.
        """

        if self.est_v2():
            return self.tier_de(nom).parametres

        return self.parametres


def _dossier_projet_v1(chemin: Path) -> Path:
    """
    Ramène une sélection (dossier projet ou fichier
    .sttproj) au dossier du projet v1.
    """

    chemin = Path(chemin)

    if chemin.suffix == ".sttproj":
        return chemin.parent

    return chemin


def creer_etude(
    dossier,
    titre: str,
    theme: str = "livre",
    gabarit_titre_1: str = (
        "Chapitre {chapitre} — {section}"
    ),
    format_version: int = ETUDE_FORMAT_VERSION
) -> EtudeOuverte:
    """
    Crée le dossier étude et sa structure.

    En v2 (P18.7c, défaut) : etude.json (version 2),
    reunions/, synthese/, parametres/ (surcharges synthèse
    uniquement) et journal_etude.json — PAS de blocs/ ni
    traitements/ (ils vivent dans le tier de chaque
    réunion, dans le projet v1).

    Le dossier peut exister et être non vide
    (ARBITRAGE_CREATION_ETUDE) — la confirmation est à la
    charge de l'UI ; le service garantit lui :

    - refus dur si le dossier contient déjà une
      étude (etude.json) ;
    - refus avant toute écriture si un fichier
      existant occupe l'emplacement d'un
      sous-dossier de l'étude ;
    - aucun fichier préexistant n'est modifié ni
      supprimé.
    """

    dossier = Path(dossier)

    if (dossier / FICHIER_ETUDE).exists():
        raise EtudeError(
            f"Le dossier {dossier} contient déjà "
            f"une étude ({FICHIER_ETUDE}) ; elle ne "
            "s'écrase pas. Ouvrez l'étude existante, "
            "ou saisissez plutôt un nom de nouveau "
            "dossier pour créer l'étude dedans."
        )

    if format_version == 2:
        sous_dossiers = (
            DOSSIER_REUNIONS,
            DOSSIER_SYNTHESE,
            DOSSIER_PARAMETRES,
        )
    else:
        sous_dossiers = (
            DOSSIER_REUNIONS,
            DOSSIER_BLOCS,
            f"{DOSSIER_BLOCS}/{DOSSIER_DECOUPAGE}",
            DOSSIER_TRAITEMENTS,
            f"{DOSSIER_TRAITEMENTS}/{DOSSIER_REFORMULATION}",
            f"{DOSSIER_TRAITEMENTS}/{DOSSIER_RESUME}",
            DOSSIER_SYNTHESE,
            DOSSIER_PARAMETRES,
        )

    #
    # Conflits de nom : un fichier existant occupant
    # l'emplacement d'un sous-dossier de l'étude
    # bloque la création — erreur claire avant
    # d'écrire quoi que ce soit.
    #
    for sous_dossier in sous_dossiers:

        chemin = dossier / sous_dossier

        if chemin.exists() and not chemin.is_dir():
            raise EtudeError(
                f"Le dossier {dossier} contient déjà "
                f"un fichier nommé « {sous_dossier} » "
                "qu'un sous-dossier de l'étude devrait "
                "occuper. Rien n'a été écrit — "
                "saisissez plutôt un nom de nouveau "
                "dossier pour créer l'étude dedans."
            )

    dossier.mkdir(parents=True, exist_ok=True)

    for sous_dossier in sous_dossiers:
        (dossier / sous_dossier).mkdir(
            parents=True,
            exist_ok=True
        )

    maintenant = horodatage_courant()

    etude_ouverte = EtudeOuverte()

    etude_ouverte.dossier = dossier
    etude_ouverte.etude = Etude(
        etude_format_version=format_version,
        titre=titre,
        theme=theme,
        gabarit_titre_1=gabarit_titre_1,
        ordre_reunions=[],
        creation=maintenant,
        modification=maintenant,
    )

    etude_ouverte._registre_v1 = RegistreFID()
    etude_ouverte.parametres = parametres_par_defaut()
    etude_ouverte.synthese = SyntheseEtude()

    #
    # Log des opérations : en v2, journal_etude.json à la
    # racine (niveau étude ; les opérations de traitement
    # de chaque réunion vont dans le journal de son tier) ;
    # en v1, traitements/journal_operations.json (historique).
    #
    if format_version == 2:
        etude_ouverte.journal = JournalEtude(
            dossier / FICHIER_JOURNAL_ETUDE
        )
    else:
        etude_ouverte.journal = JournalEtude(
            dossier / DOSSIER_TRAITEMENTS
            / FICHIER_JOURNAL
        )

    etude_ouverte.journal.initialiser()

    sauvegarder_etude(etude_ouverte)

    return etude_ouverte


def _dict_reunion_v2(reunion: ReunionEtude) -> dict:
    """
    ``reunions/<nom>.json`` en v2 : titre_1 et chemins ;
    resume_valide a migré vers le tier (P18.7c).
    """

    data = reunion.to_dict()
    data.pop("resume_valide", None)

    return data


def _parametres_etude_v2_dict(
    parametres: ParametresEtude
) -> dict:
    """
    ``parametres/parametres.json`` d'une étude v2 :
    surcharges de SYNTHÈSE uniquement (P18.7c/§8bis) —
    tous les autres paramètres vivent dans le tier de
    chaque réunion.
    """

    return {
        "synthese": dict(parametres.synthese),
    }


def sauvegarder_etude(etude_ouverte: EtudeOuverte) -> None:
    """
    Écrit les fichiers de NIVEAU ÉTUDE sur disque.

    **Aucune écriture en retour dans les tiers** (P18.7) :
    ni l'étude ni l'ouvrage n'écrivent jamais dans le tier
    d'une réunion — seules les opérations sur les
    traitements de la réunion y écrivent (elles
    sauvegardent le tier explicitement). En mode autonome,
    seule la sauvegarde du tier a un effet.

    Seuls les fichiers de l'étude sont écrits : jamais
    un projet v1 référencé (hors création additive de
    son tier, faite à l'attachement).
    """

    if etude_ouverte.mode_autonome:

        for tier in etude_ouverte.tiers.values():
            sauvegarder_tier(tier)

        return

    dossier = etude_ouverte.dossier

    if dossier is None or etude_ouverte.etude is None:
        raise EtudeError(
            "Étude non initialisée : rien à sauvegarder."
        )

    etude_ouverte.etude.modification = (
        horodatage_courant()
    )

    v2 = etude_ouverte.est_v2()

    _ecrire_json(
        dossier / FICHIER_ETUDE,
        etude_ouverte.etude.to_dict()
    )

    for nom, reunion in etude_ouverte.reunions.items():
        _ecrire_json(
            dossier / DOSSIER_REUNIONS
            / f"{nom}.json",
            (
                _dict_reunion_v2(reunion)
                if v2
                else reunion.to_dict()
            ),
        )

    if not v2:
        #
        # v1 (historique) : blocs/ et traitements/ reconstruits
        # depuis les tiers. En v2 ces dossiers n'existent
        # plus au niveau étude.
        #
        _ecrire_json(
            dossier / DOSSIER_BLOCS
            / FICHIER_REGISTRE_FID,
            etude_ouverte._registre_v1.to_dict()
        )

        for nom, tier in etude_ouverte.tiers.items():

            if tier.decoupage is not None:
                _ecrire_json(
                    dossier / DOSSIER_BLOCS
                    / DOSSIER_DECOUPAGE
                    / f"{nom}.json",
                    tier.decoupage.to_dict()
                )

            for resultat in (
                tier.reformulations.values()
            ):
                _ecrire_json(
                    dossier / DOSSIER_TRAITEMENTS
                    / DOSSIER_REFORMULATION
                    / f"{resultat.fid}.json",
                    resultat.to_dict()
                )

            if tier.resume is not None:
                _ecrire_json(
                    dossier / DOSSIER_TRAITEMENTS
                    / DOSSIER_RESUME
                    / f"{nom}.json",
                    tier.resume.to_dict()
                )

    _ecrire_json(
        dossier / DOSSIER_SYNTHESE
        / FICHIER_SYNTHESE,
        etude_ouverte.synthese.to_dict()
    )

    _ecrire_json(
        dossier / DOSSIER_PARAMETRES
        / FICHIER_PARAMETRES,
        (
            _parametres_etude_v2_dict(
                etude_ouverte.parametres
            )
            if v2
            else etude_ouverte.parametres.to_dict()
        ),
    )


def ouvrir_etude(dossier) -> EtudeOuverte:
    """
    Ouvre une étude existante.

    - étude **v1** : migration one-shot v1→v2 à
      l'ouverture (P18.7f, §11 — sauvegarde complète dans
      sauvegardes\\, éclatement par réunion dans les
      tiers, requalification des références de blocs,
      contrôle d'intégrité avant toute suppression) ;
    - étude **v2** : chargement direct ; le tier de chaque
      réunion joignable est ouvert dans son projet v1
      (créé additif s'il manque, avec etudes[] renseigné).

    Chaque réunion est résolue par ordre : chemin relatif
    au dossier étude, puis chemin absolu historique ; une
    réunion introuvable place l'étude en mode dégradé sans
    bloquer les autres.

    Toute divergence etudes[] du tier vs ordre_reunions est
    consignée dans ``divergences`` (signalée, jamais
    auto-corrigée).

    Lève EtudeFormatError si le dossier n'est pas une
    étude ou si un fichier viole le schéma.
    """

    dossier = Path(dossier)

    fichier_etude = dossier / FICHIER_ETUDE

    if not fichier_etude.exists():
        raise EtudeFormatError(
            str(fichier_etude),
            "fichier etude.json introuvable : "
            "ce dossier n'est pas une étude"
        )

    donnees = _lire_json(fichier_etude)
    valider_etude(donnees, str(fichier_etude))

    if donnees["etude_format_version"] == 1:
        #
        # P18.7f (§11) : migration one-shot v1→v2 à
        # l'ouverture, puis relecture en v2.
        #
        from services.migration_etude import (
            migrer_etude_v1_vers_v2,
        )

        migrer_etude_v1_vers_v2(dossier)

        donnees = _lire_json(fichier_etude)
        valider_etude(donnees, str(fichier_etude))

    etude_ouverte = EtudeOuverte()
    etude_ouverte.dossier = dossier
    etude_ouverte.etude = Etude.from_dict(donnees)

    v2 = etude_ouverte.est_v2()

    #
    # Réunions : seuls les fichiers listés dans
    # ordre_reunions font partie de l'étude.
    #

    for nom in etude_ouverte.etude.ordre_reunions:

        chemin_reunion = (
            dossier / DOSSIER_REUNIONS
            / f"{nom}.json"
        )

        if not chemin_reunion.exists():
            raise EtudeFormatError(
                str(chemin_reunion),
                "réunion référencée par ordre_reunions "
                f"mais absente : {nom}"
            )

        donnees_reunion = _lire_json(chemin_reunion)
        valider_reunion(
            donnees_reunion,
            str(chemin_reunion)
        )

        etude_ouverte.reunions[nom] = (
            ReunionEtude.from_dict(
                nom,
                donnees_reunion
            )
        )

    #
    # Paramètres.
    #

    chemin_parametres = (
        dossier / DOSSIER_PARAMETRES
        / FICHIER_PARAMETRES
    )

    if chemin_parametres.exists():

        donnees_parametres = _lire_json(
            chemin_parametres
        )

        if v2:
            valider_parametres_synthese_seule(
                donnees_parametres,
                str(chemin_parametres)
            )

            # Surcharge synthèse seule : les autres
            # sections prennent les défauts (elles vivent
            # dans les tiers en v2).
            defauts = parametres_par_defaut()
            defauts.synthese = dict(
                donnees_parametres["synthese"]
            )
            etude_ouverte.parametres = defauts

        else:
            valider_parametres(
                donnees_parametres,
                str(chemin_parametres)
            )
            etude_ouverte.parametres = (
                ParametresEtude.from_dict(
                    donnees_parametres
                )
            )

    else:
        etude_ouverte.parametres = parametres_par_defaut()

    #
    # Synthèse d'étude.
    #

    chemin_synthese = (
        dossier / DOSSIER_SYNTHESE / FICHIER_SYNTHESE
    )

    if chemin_synthese.exists():

        donnees_synthese = _lire_json(chemin_synthese)
        valider_synthese(
            donnees_synthese,
            str(chemin_synthese)
        )

        etude_ouverte.synthese = (
            SyntheseEtude.from_dict(donnees_synthese)
        )

    else:
        etude_ouverte.synthese = SyntheseEtude()

    #
    # Log des opérations de niveau étude.
    #

    if v2:
        etude_ouverte.journal = JournalEtude(
            dossier / FICHIER_JOURNAL_ETUDE
        )
    else:
        etude_ouverte.journal = JournalEtude(
            dossier / DOSSIER_TRAITEMENTS
            / FICHIER_JOURNAL
        )

    #
    # Résolution des réunions : relatif, puis absolu,
    # puis mode dégradé. Le tier de chaque réunion
    # joignable est ouvert dans son projet v1 (créé
    # additif s'il manque).
    #

    for nom in etude_ouverte.etude.ordre_reunions:

        reunion = etude_ouverte.reunions[nom]

        chemin_resolu = _resoudre_reunion(
            etude_ouverte,
            reunion
        )

        etude_ouverte.chemins_resolus[nom] = (
            chemin_resolu
        )

        if chemin_resolu is None:
            etude_ouverte.reunions_introuvables.append(
                nom
            )
            continue

        dossier_projet = _dossier_projet_v1(
            Path(chemin_resolu)
        )

        tier = ouvrir_tier(dossier_projet)

        if tier is None:

            #
            # Tier absent : construit EN MÉMOIRE, sans
            # aucune écriture dans le projet v1 (ouvrir
            # une étude ne modifie jamais un projet v1).
            # Le tier se matérialisera à la première
            # opération sur les traitements de la réunion.
            #
            from services.tier_reunion import (
                nouveau_tier,
            )

            tier = nouveau_tier(
                dossier_projet,
                nom=nom,
                parametres=(
                    ParametresEtude.from_dict(
                        etude_ouverte.parametres.to_dict()
                    )
                    if not v2
                    else parametres_par_defaut()
                ),
            )

        if not v2:
            # v1 : resume_valide reste porté par la
            # référence d'étude.
            tier.reunion.resume_valide = (
                reunion.resume_valide
            )

        etude_ouverte.tiers[nom] = tier

    if not v2:

        #
        # v1 (avant migration P18.7f) : lecture de l'ancien
        # layout étude (blocs/, traitements/) — éclaté en
        # mémoire dans les tiers par réunion.
        #
        _charger_v1_dans_tiers(etude_ouverte, dossier)

    #
    # P18.7d : signalement des divergences etudes[] du
    # tier vs ordre_reunions de l'étude — jamais
    # auto-corrigé.
    #
    if v2:
        #
        # Signalement des divergences etudes[] du tier
        # vs ordre_reunions — AVANT toute inscription en
        # mémoire, et jamais auto-corrigé.
        #
        _signaler_divergences(etude_ouverte)

        #
        # Inscription en mémoire seulement (aucune
        # écriture à l'ouverture) : le tier se
        # matérialisera dans le projet v1 à la première
        # opération sur les traitements de la réunion.
        #
        import os as _os

        for nom in etude_ouverte.etude.ordre_reunions:

            tier = etude_ouverte.tiers.get(nom)

            if tier is None:
                continue

            dossier_projet = tier.dossier_projet

            try:
                relatif = _os.path.relpath(
                    str(dossier.resolve()),
                    str(dossier_projet.resolve())
                ).replace("\\", "/")
            except (ValueError, OSError):
                relatif = _normaliser_chemin(
                    str(dossier.resolve())
                )

            if relatif not in tier.reunion.etudes:
                tier.reunion.etudes.append(relatif)

    return etude_ouverte


def _charger_v1_dans_tiers(
    etude_ouverte: EtudeOuverte,
    dossier: Path
) -> None:
    """
    Charge l'ancien layout v1 (blocs/, traitements/ au
    niveau étude) en mémoire, éclaté par réunion dans les
    tiers. Le registre global est conservé tel quel
    (``_registre_v1``) ; chaque tier reçoit le sous-ensemble
    de ses entrées. Aucune écriture disque ici.
    """

    #
    # Registre global.
    #

    chemin_registre = (
        dossier / DOSSIER_BLOCS
        / FICHIER_REGISTRE_FID
    )

    if chemin_registre.exists():

        donnees = _lire_json(chemin_registre)
        valider_registre_fid(donnees, str(chemin_registre))
        etude_ouverte._registre_v1 = (
            RegistreFID.from_dict(donnees)
        )

    else:
        etude_ouverte._registre_v1 = RegistreFID()

    registre = etude_ouverte._registre_v1

    #
    # Découpages.
    #

    dossier_decoupage = (
        dossier / DOSSIER_BLOCS / DOSSIER_DECOUPAGE
    )

    if dossier_decoupage.exists():

        for chemin in sorted(
            dossier_decoupage.glob("*.json")
        ):

            donnees = _lire_json(chemin)
            valider_decoupage(donnees, str(chemin))

            decoupage = DecoupageReunion.from_dict(
                donnees
            )

            nom = decoupage.reunion

            if nom in etude_ouverte.tiers:
                etude_ouverte.tiers[nom].decoupage = (
                    decoupage
                )

    #
    # Reformulations (par FID) : aiguillées vers le tier
    # de la réunion du registre.
    #

    dossier_reformulation = (
        dossier / DOSSIER_TRAITEMENTS
        / DOSSIER_REFORMULATION
    )

    if dossier_reformulation.exists():

        for chemin in sorted(
            dossier_reformulation.glob("*.json")
        ):

            donnees = _lire_json(chemin)
            valider_reformulation(donnees, str(chemin))

            resultat = ResultatReformulation.from_dict(
                donnees
            )

            entree = registre.entrees.get(resultat.fid)
            nom = (
                entree.reunion
                if entree is not None
                else resultat.reunion
            )

            resultat.reunion = nom or ""

            if nom in etude_ouverte.tiers:
                etude_ouverte.tiers[
                    nom
                ].reformulations[resultat.fid] = resultat

            # Le registre de chaque tier reçoit le
            # sous-ensemble de ses entrées.
            if nom in etude_ouverte.tiers and entree:
                etude_ouverte.tiers[
                    nom
                ].registre.entrees[resultat.fid] = entree

    #
    # Résumé par réunion.
    #

    dossier_resume = (
        dossier / DOSSIER_TRAITEMENTS
        / DOSSIER_RESUME
    )

    if dossier_resume.exists():

        for chemin in sorted(
            dossier_resume.glob("*.json")
        ):

            donnees = _lire_json(chemin)
            valider_resume(donnees, str(chemin))

            resultat = ResultatResume.from_dict(donnees)

            if resultat.reunion in etude_ouverte.tiers:
                etude_ouverte.tiers[
                    resultat.reunion
                ].resume = resultat

    #
    # Registres des tiers : sous-ensembles du global.
    #

    for nom, tier in etude_ouverte.tiers.items():

        entrees = {
            fid: entree
            for fid, entree in registre.entrees.items()
            if entree.reunion == nom
        }

        prochain = (
            max(entrees.keys(), default=0) + 1
            if entrees
            else 1
        )

        tier.registre = RegistreFID(
            prochain_fid=max(
                prochain,
                tier.registre.prochain_fid
            ),
            entrees=entrees,
        )

    #
    # Paramètres de l'étude v1 : partagés par tous les
    # tiers en mémoire (la migration f les éclatera).
    #

    for tier in etude_ouverte.tiers.values():
        tier.parametres = etude_ouverte.parametres


def _signaler_divergences(etude_ouverte: EtudeOuverte) -> None:
    """
    P18.7d : à l'ouverture, toute divergence entre
    etudes[] du tier d'une réunion et ordre_reunions de
    l'étude est consignée dans ``divergences`` —
    SIGNALÉE, jamais auto-corrigée.
    """

    dossier = etude_ouverte.dossier.resolve()

    for nom in etude_ouverte.etude.ordre_reunions:

        tier = etude_ouverte.tiers.get(nom)

        if tier is None:
            continue

        etudes_tier = set()

        for chemin in tier.reunion.etudes:

            candidat = (
                (tier.dossier_projet / chemin)
                if not Path(chemin).is_absolute()
                else Path(chemin)
            )

            try:
                etudes_tier.add(str(candidat.resolve()))
            except OSError:
                etudes_tier.add(str(candidat))

        if str(dossier) not in etudes_tier:
            etude_ouverte.divergences.append(
                f"Réunion « {nom} » : le tier liste "
                f"etudes={tier.reunion.etudes} mais "
                "l'étude courante n'y figure pas "
                "(ordre_reunions)."
            )

        for autre in etudes_tier:
            if autre != str(dossier):
                etude_ouverte.divergences.append(
                    f"Réunion « {nom} » : le tier est "
                    f"aussi rattaché à {autre}, hors "
                    "ordre_reunions de cette étude."
                )


def _resoudre_reunion(
    etude_ouverte: EtudeOuverte,
    reunion: ReunionEtude
):
    """
    Résout le projet v1 d'une réunion :
    1. chemin relatif au dossier étude ;
    2. chemin absolu historique.

    Retourne le dossier projet résolu ou None.
    À la première résolution réussie par chemin relatif,
    le chemin absolu est mémorisé en secours (persisté à la
    prochaine sauvegarde).
    """

    dossier = etude_ouverte.dossier

    chemin_relatif = (
        dossier / reunion.chemin_projet
    )

    if _est_projet_v1(chemin_relatif):

        if reunion.chemin_absolu is None:
            reunion.chemin_absolu = (
                _normaliser_chemin(
                    str(chemin_relatif.resolve())
                )
            )

        return _dossier_projet_v1(
            chemin_relatif.resolve()
        )

    if reunion.chemin_absolu is not None:

        chemin_absolu = Path(reunion.chemin_absolu)

        if _est_projet_v1(chemin_absolu):
            return _dossier_projet_v1(
                chemin_absolu.resolve()
            )

    return None


def _est_projet_v1(chemin: Path) -> bool:
    """
    Un dossier est un projet v1 joignable s'il contient
    un fichier project.sttproj (ou tout .sttproj).
    """

    dossier = _dossier_projet_v1(Path(chemin))

    if not dossier.is_dir():
        return False

    if (dossier / "project.sttproj").exists():
        return True

    return any(dossier.glob("*.sttproj"))


def fichier_projet_v1(
    etude_ouverte: EtudeOuverte,
    nom: str
):
    """
    Chemin du fichier project.sttproj d'une réunion
    joignable ; None si la réunion est introuvable.
    """

    dossier = etude_ouverte.chemins_resolus.get(nom)

    if dossier is None:
        return None

    dossier = Path(dossier)

    chemin = dossier / "project.sttproj"

    if chemin.exists():
        return chemin

    correspondances = sorted(
        dossier.glob("*.sttproj")
    )

    if correspondances:
        return correspondances[0]

    return None


def relocaliser_reunion(
    etude_ouverte: EtudeOuverte,
    nom: str,
    nouveau_chemin
) -> None:
    """
    Relocalisation guidée : met à jour la référence d'une
    réunion vers un projet v1 désigné par l'utilisateur.
    """

    if nom not in etude_ouverte.reunions:
        raise EtudeError(f"Réunion inconnue : {nom}")

    dossier_projet = _dossier_projet_v1(
        Path(nouveau_chemin)
    )

    if not _est_projet_v1(dossier_projet):
        raise EtudeError(
            f"{dossier_projet} n'est pas un projet v1 "
            "(fichier .sttproj attendu)."
        )

    reunion = etude_ouverte.reunions[nom]

    reunion.chemin_projet = _chemin_relatif(
        etude_ouverte.dossier,
        dossier_projet
    )

    reunion.chemin_absolu = _normaliser_chemin(
        str(dossier_projet.resolve())
    )

    etude_ouverte.chemins_resolus[nom] = dossier_projet

    #
    # Le tier suit la réunion : ouvert dans le nouveau
    # projet (créé additif s'il manque).
    #
    tier = ouvrir_tier(dossier_projet)

    if tier is None:
        tier = creer_tier(dossier_projet, nom=nom)

    if etude_ouverte.est_v2():
        tier.enregistrer_etude(
            etude_ouverte.dossier,
            ajouter=True
        )

    etude_ouverte.tiers[nom] = tier

    if nom in etude_ouverte.reunions_introuvables:
        etude_ouverte.reunions_introuvables.remove(nom)


def ajouter_reunion(
    etude_ouverte: EtudeOuverte,
    chemin_projet,
    titre_1: str = "",
    date: str = None,
    numero: int = None
) -> str:
    """
    Ajoute un projet v1 existant comme réunion de
    l'étude (référence, jamais copie) et l'ajoute en
    fin d'ordre de lecture.

    P18.7d : à l'attachement, la réunion HÉRITE
    TOTALEMENT et SILENCIEUSEMENT de son tier
    (transcriptstudio\\ dans le projet v1) — tout son
    travail est conservé tel quel ; si le projet n'a
    pas encore de tier, il est créé (vide, paramètres
    par défaut) et l'étude y est enregistrée (etudes[]).

    Le nom de la réunion dérive du dossier projet. Un
    même projet ne peut pas être référencé deux fois
    dans la même étude.

    Retourne le nom de la réunion.
    """

    dossier_projet = _dossier_projet_v1(
        Path(chemin_projet)
    )

    if not _est_projet_v1(dossier_projet):
        raise EtudeError(
            f"{dossier_projet} n'est pas un projet v1 "
            "(fichier .sttproj attendu)."
        )

    dossier_projet = dossier_projet.resolve()

    for nom, reunion in etude_ouverte.reunions.items():

        chemin_deja_pris = (
            etude_ouverte.chemins_resolus.get(nom)
        )

        if chemin_deja_pris is None:
            continue

        if (
            Path(chemin_deja_pris).resolve()
            == dossier_projet
        ):
            raise EtudeError(
                "Ce projet v1 est déjà référencé par "
                f"la réunion {nom} de cette étude."
            )

    nom = normaliser_nom_fichier(dossier_projet.name)

    if not nom:
        nom = normaliser_nom_fichier(
            f"reunion_{len(etude_ouverte.reunions) + 1}"
        )

    if nom in etude_ouverte.reunions:
        raise EtudeError(
            f"Une réunion nommée {nom} existe déjà "
            "dans cette étude."
        )

    if numero is None:

        numeros = [
            reunion.numero
            for reunion
            in etude_ouverte.reunions.values()
        ]

        numero = max(numeros, default=0) + 1

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    #
    # Tier de la réunion : héritage total silencieux —
    # le tier existant est repris tel quel (aucune
    # copie, aucune perte) ; sinon il est créé.
    #
    tier = ouvrir_tier(dossier_projet)

    if tier is None:
        tier = creer_tier(
            dossier_projet,
            nom=nom,
            parametres=(
                ParametresEtude.from_dict(
                    etude_ouverte.parametres.to_dict()
                )
                if not etude_ouverte.est_v2()
                else parametres_par_defaut()
            ),
        )

    if etude_ouverte.est_v2():
        tier.enregistrer_etude(
            etude_ouverte.dossier,
            ajouter=True
        )

        #
        # Une seule réunion : les paramètres de traitement
        # en mémoire sont ceux de l'étude (objet partagé) —
        # à partir de la deuxième réunion, chaque tier a sa
        # copie propre.
        #
        if len(etude_ouverte.reunions) == 0:
            tier.parametres = etude_ouverte.parametres
        else:
            tier.parametres = ParametresEtude.from_dict(
                etude_ouverte.parametres.to_dict()
            )

    reunion = ReunionEtude(
        nom=nom,
        reference=f"{nom}.json",
        chemin_projet=_chemin_relatif(
            etude_ouverte.dossier,
            dossier_projet
        ),
        chemin_absolu=_normaliser_chemin(
            str(dossier_projet)
        ),
        date=date,
        numero=numero,
        titre_1=titre_1,
        resume_valide=tier.reunion.resume_valide,
    )

    etude_ouverte.reunions[nom] = reunion
    etude_ouverte.chemins_resolus[nom] = dossier_projet
    etude_ouverte.tiers[nom] = tier

    etude_ouverte.etude.ordre_reunions.append(nom)

    return nom


def retirer_reunion(
    etude_ouverte: EtudeOuverte,
    nom: str
) -> None:
    """
    Retire une réunion de l'étude.

    - **v2 (P18.7d)** : détachement NON DESTRUCTIF — la
      référence disparaît de l'étude et l'étude est
      retirée d'etudes[] du tier, mais la réunion GARDE
      TOUT SON TRAVAIL : le tier (découpage, registre,
      reformulations, résumé, journal, paramètres) reste
      intact dans le projet v1, qui n'est pas touché
      sinon.
    - **v1** : comportement historique (la référence et
      les résultats d'étude disparaissent ; le projet v1
      et le registre ne sont pas touchés).
    """

    if nom not in etude_ouverte.reunions:
        raise EtudeError(f"Réunion inconnue : {nom}")

    dossier = etude_ouverte.dossier

    etude_ouverte.reunions.pop(nom)
    etude_ouverte.chemins_resolus.pop(nom, None)

    if nom in etude_ouverte.reunions_introuvables:
        etude_ouverte.reunions_introuvables.remove(nom)

    etude_ouverte.etude.ordre_reunions.remove(nom)

    tier = etude_ouverte.tiers.pop(nom, None)

    if etude_ouverte.est_v2():

        #
        # Détachement non destructif : la référence
        # disparaît du dossier étude, l'étude se retire
        # d'etudes[] du tier, et le reste du tier est
        # conservé tel quel dans le projet v1.
        #
        if not etude_ouverte.mode_autonome:
            (dossier / DOSSIER_REUNIONS
             / f"{nom}.json").unlink(missing_ok=True)

            if tier is not None:
                tier.enregistrer_etude(
                    dossier,
                    ajouter=False
                )

        return

    #
    # v1 (historique).
    #

    etude_ouverte.decoupages.pop(nom, None)
    etude_ouverte.resumes.pop(nom, None)

    fids = [
        fid
        for fid, entree
        in etude_ouverte._registre_v1.entrees.items()
        if entree.reunion == nom
    ]

    for fid in fids:
        if tier is not None:
            tier.reformulations.pop(fid, None)

    chemins = [
        dossier / DOSSIER_REUNIONS / f"{nom}.json",
        dossier / DOSSIER_BLOCS
        / DOSSIER_DECOUPAGE / f"{nom}.json",
        dossier / DOSSIER_TRAITEMENTS
        / DOSSIER_RESUME / f"{nom}.json",
    ]

    chemins.extend(
        dossier / DOSSIER_TRAITEMENTS
        / DOSSIER_REFORMULATION / f"{fid}.json"
        for fid in fids
    )

    for chemin in chemins:
        chemin.unlink(missing_ok=True)


def deplacer_reunion(
    etude_ouverte: EtudeOuverte,
    nom: str,
    nouvel_index: int
) -> None:
    """
    Déplace une réunion dans l'ordre de lecture.
    """

    ordre = etude_ouverte.etude.ordre_reunions

    if nom not in ordre:
        raise EtudeError(f"Réunion inconnue : {nom}")

    ancien_index = ordre.index(nom)

    ordre.pop(ancien_index)

    nouvel_index = max(
        0,
        min(nouvel_index, len(ordre))
    )

    ordre.insert(nouvel_index, nom)


def attribuer_fid(
    etude_ouverte: EtudeOuverte,
    reunion: str
) -> int:
    """
    Attribue un nouveau FID pour un bloc de la réunion.

    P18.7b : en v2, le FID est un entier séquentiel DU
    REGISTRE DE LA RÉUNION (dans le tier) — identité de
    bloc = (réunion, FID), jamais réutilisé. En v1, le
    registre global de l'étude fait encore autorité.
    """

    if etude_ouverte.est_v2():
        tier = etude_ouverte.tier_de(reunion)
        registre = tier.registre
    else:
        registre = etude_ouverte._registre_v1

    fid = registre.prochain_fid

    registre.prochain_fid = fid + 1

    entree = EntreeFID(
        fid=fid,
        reunion=reunion,
        cree=horodatage_courant(),
        actif=True,
        fin=None,
    )

    registre.entrees[fid] = entree

    if etude_ouverte.est_v2():
        sauvegarder_tier(tier)

    return fid


def _entree_fid(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    fid: int
) -> EntreeFID:

    registre = etude_ouverte.registre_de(reunion)

    entree = registre.entrees.get(fid)

    if entree is None:
        raise EtudeError(
            f"FID {fid} inconnu de la réunion {reunion}"
        )

    return entree


def _marquer_fid_inactif_impl(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    fid: int
) -> None:
    """
    Marque un FID comme inactif (bloc supprimé ou
    fusionné). Le couple (réunion, FID) reste au registre
    de la réunion, les résultats associés aussi.
    """

    entree = _entree_fid(etude_ouverte, reunion, fid)

    entree.actif = False
    entree.fin = horodatage_courant()

    if etude_ouverte.est_v2():
        sauvegarder_tier(etude_ouverte.tier_de(reunion))


def _reactiver_fid_impl(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    fid: int
) -> None:
    """
    Réactive un FID inactif (dé-fusion : le bloc
    redevient la segmentation active avec ses
    données d'origine — même discours, même couple
    (réunion, FID)).
    """

    entree = _entree_fid(etude_ouverte, reunion, fid)

    entree.actif = True
    entree.fin = None

    if etude_ouverte.est_v2():
        sauvegarder_tier(etude_ouverte.tier_de(reunion))


def enregistrer_decoupage(
    etude_ouverte: EtudeOuverte,
    decoupage: DecoupageReunion
) -> None:
    """
    Enregistre la segmentation d'une réunion — dans
    SON TIER (``blocs/decoupage.json`` du projet v1 en
    v2).

    Chaque bloc doit porter un FID attribué du registre
    de la réunion ; le texte source est immuable après
    enregistrement.
    """

    if decoupage.reunion not in etude_ouverte.reunions:
        raise EtudeError(
            f"Réunion inconnue : {decoupage.reunion}"
        )

    registre = etude_ouverte.registre_de(
        decoupage.reunion
    )

    for bloc in decoupage.blocs:

        entree = registre.entrees.get(bloc.fid)

        if entree is None:
            raise EtudeError(
                f"FID {bloc.fid} absent du registre de "
                f"la réunion {decoupage.reunion}"
            )

        if entree.reunion != decoupage.reunion:
            raise EtudeError(
                f"FID {bloc.fid} attribué à la réunion "
                f"{entree.reunion}, pas à "
                f"{decoupage.reunion}"
            )

        bloc.source = normaliser_sauts_paragraphe(
            bloc.source
        )

    tier = etude_ouverte.tier_de(decoupage.reunion)

    tier.decoupage = decoupage

    if etude_ouverte.est_v2():
        sauvegarder_tier(tier)


def _couple_contexte(
    reunion: str,
    contexte: list
) -> list:
    """
    Requalifie une liste de références de contexte en
    couples (réunion, FID) — objets ``{"reunion", "fid"}``
    (P18.7b). Les entiers nus (v1) sont acceptés.
    """

    couples = []

    for entree in contexte or []:

        if isinstance(entree, dict):
            couples.append(
                {
                    "reunion": str(
                        entree.get("reunion", reunion)
                    ),
                    "fid": int(entree["fid"]),
                }
            )
        else:
            couples.append(
                {
                    "reunion": reunion,
                    "fid": int(entree),
                }
            )

    return couples


def _ajouter_version_reformulation_impl(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    fid: int,
    texte: str,
    type_version: str = "passe",
    consigne: str = None,
    selection: dict = None,
    stats: dict = None,
    contexte: list = None,
    modele: str = None
) -> VersionReformulation:
    """
    Ajoute une version au résultat de reformulation d'un
    bloc — dans le TIER de la réunion
    (``traitements/reformulation/<FID>.json`` du projet v1
    en v2). L'historique est complet : jamais d'écrasement.

    ``reunion`` + ``fid`` : identité de bloc (P18.7b).
    ``contexte`` : références de la fenêtre glissante,
    requalifiées en couples (réunion, FID).

    Règle d'invariance 4 de la spec moteur : l'opération
    produit exactement une entrée de log, horodatée,
    avant retour à l'UI (reformulation_bloc, ou
    edition_manuelle pour une correction à la main) —
    dans le journal DU TIER.
    """

    entree = _entree_fid(etude_ouverte, reunion, fid)

    tier = etude_ouverte.tier_de(reunion)

    resultat = tier.reformulations.get(fid)

    if resultat is None:
        resultat = ResultatReformulation(
            fid=fid,
            reunion=reunion
        )
        tier.reformulations[fid] = resultat

    numeros = [
        version.numero
        for version in resultat.versions
    ]

    version = VersionReformulation(
        numero=max(numeros, default=0) + 1,
        texte=normaliser_sauts_paragraphe(texte),
        horodatage=horodatage_courant(),
        type=type_version,
        consigne=consigne,
        selection=selection,
        stats=stats,
        validation=None,
        contexte=_couple_contexte(reunion, contexte),
    )

    resultat.versions.append(version)

    etude_ouverte.journal_traitement(reunion).ajouter(
        TYPE_EDITION_MANUELLE
        if type_version == "edition_manuelle"
        else TYPE_REFORMULATION_BLOC,
        fid=fid,
        reunion=reunion,
        modele=modele,
        version=version.numero,
        resultat=RESULTAT_SUCCES,
        message=(
            f"Version {version.numero} "
            f"({type_version})"
        ),
        stats=stats,
        extras={
            "type_version": type_version,
        }
    )

    if etude_ouverte.est_v2():
        sauvegarder_tier(tier)

    return version


def _valider_version_reformulation_impl(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    fid: int,
    numero: int,
    validateur: str
) -> None:
    """
    Valide une version précise du résultat d'un bloc :
    la validation se porte sur la version, qui devient
    la version figée du bloc.
    """

    tier = etude_ouverte.tier_de(reunion)

    resultat = tier.reformulations.get(fid)

    if resultat is None:
        raise EtudeError(
            f"Aucun résultat de reformulation "
            f"pour le bloc ({reunion}, {fid})"
        )

    for version in resultat.versions:

        if version.numero == numero:

            version.validation = Validation(
                statut="valide",
                horodatage=horodatage_courant(),
                validateur=validateur,
            )

            etude_ouverte.journal_traitement(
                reunion
            ).ajouter(
                TYPE_VALIDATION,
                fid=fid,
                reunion=reunion,
                version=numero,
                resultat=RESULTAT_SUCCES,
                message=(
                    f"Version {numero} validée "
                    f"par {validateur}."
                )
            )

            if etude_ouverte.est_v2():
                sauvegarder_tier(tier)

            return

    raise EtudeError(
        f"Version {numero} introuvable "
        f"pour le bloc ({reunion}, {fid})"
    )


def _devalider_version_reformulation_impl(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    fid: int,
    numero: int
) -> None:
    """
    Dévalide une version (le bloc redevient
    modifiable) : une entrée de log devalidation
    est consignée.
    """

    tier = etude_ouverte.tier_de(reunion)

    resultat = tier.reformulations.get(fid)

    if resultat is None:
        raise EtudeError(
            f"Aucun résultat de reformulation "
            f"pour le bloc ({reunion}, {fid})"
        )

    for version in resultat.versions:

        if version.numero == numero:

            version.validation = None

            etude_ouverte.journal_traitement(
                reunion
            ).ajouter(
                TYPE_DEVALIDATION,
                fid=fid,
                reunion=reunion,
                version=numero,
                resultat=RESULTAT_SUCCES,
                message=(
                    f"Version {numero} dévalidée."
                )
            )

            if etude_ouverte.est_v2():
                sauvegarder_tier(tier)

            return

    raise EtudeError(
        f"Version {numero} introuvable "
        f"pour le bloc ({reunion}, {fid})"
    )



#
# Wrappers publics : signature unique (etude, reunion, fid) —
# P20 fin (ARBITRAGE_P18_7_ECARTS, écart 5) : le FID nu
# n'est plus accepté en lecture.
#


def marquer_fid_inactif(
    etude_ouverte,
    reunion: str,
    fid: int
) -> None:
    return _marquer_fid_inactif_impl(
        etude_ouverte,
        reunion,
        fid
    )


def reactiver_fid(
    etude_ouverte,
    reunion: str,
    fid: int
) -> None:
    return _reactiver_fid_impl(
        etude_ouverte,
        reunion,
        fid
    )


def ajouter_version_reformulation(
    etude_ouverte,
    reunion: str,
    fid: int,
    *args,
    **kwargs
) -> VersionReformulation:
    """
    P20 fin : signature unique (etude, reunion, fid, ...) —
    le FID nu n'est plus accepté (ARBITRAGE_P18_7_ECARTS,
    écart 5).
    """
    return _ajouter_version_reformulation_impl(
        etude_ouverte,
        reunion,
        fid,
        *args,
        **kwargs
    )


def valider_version_reformulation(
    etude_ouverte,
    reunion: str,
    fid: int,
    *args,
    numero=None,
    validateur=None
) -> None:
    """P20 fin : signature unique (etude, reunion, fid, ...)."""
    reste = list(args)
    if reste and numero is None:
        numero = reste.pop(0)
    if reste and validateur is None:
        validateur = reste.pop(0)
    return _valider_version_reformulation_impl(
        etude_ouverte,
        reunion,
        fid,
        numero=numero,
        validateur=validateur
    )


def devalider_version_reformulation(
    etude_ouverte,
    reunion: str,
    fid: int,
    *args,
    numero=None
) -> None:
    """P20 fin : signature unique (etude, reunion, fid, ...)."""
    reste = list(args)
    if reste and numero is None:
        numero = reste.pop(0)
    return _devalider_version_reformulation_impl(
        etude_ouverte,
        reunion,
        fid,
        numero=numero
    )


def ajouter_version_resume(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    texte: str,
    source: str,
    stats: dict = None,
    origine: str = "generation",
    consigne: str = None
) -> VersionResume:
    """
    Ajoute une version au résumé d'une réunion — dans
    SON TIER (``traitements/resume.json`` du projet v1
    en v2). La source utilisée est stockée avec le
    résultat ; ``origine`` : generation | relance |
    relance_ciblee | edition_manuelle (stats None
    pour une édition manuelle).
    """

    if reunion not in etude_ouverte.reunions:
        raise EtudeError(f"Réunion inconnue : {reunion}")

    tier = etude_ouverte.tier_de(reunion)

    resultat = tier.resume

    if resultat is None:
        resultat = ResultatResume(reunion=reunion)
        tier.resume = resultat

    numeros = [
        version.numero
        for version in resultat.versions
    ]

    version = VersionResume(
        numero=max(numeros, default=0) + 1,
        texte=normaliser_sauts_paragraphe(texte),
        source=source,
        horodatage=horodatage_courant(),
        stats=stats,
        origine=origine,
        consigne=consigne,
        validation=None,
    )

    resultat.versions.append(version)

    etude_ouverte.journal_traitement(reunion).ajouter(
        TYPE_EDITION_MANUELLE
        if origine == "edition_manuelle"
        else TYPE_RESUME,
        fid=None,
        reunion=reunion,
        version=version.numero,
        resultat=RESULTAT_SUCCES,
        message=(
            f"Résumé version {version.numero} "
            f"({origine}, source : {source})"
        ),
        stats=stats,
        extras={
            "source": source,
            "origine": origine,
        }
    )

    if etude_ouverte.est_v2():
        sauvegarder_tier(tier)

    return version


def valider_version_resume(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    numero: int,
    validateur: str
) -> None:
    """
    Valide une version précise du résumé d'une réunion
    (resume_valide devient True — porté par le TIER de
    la réunion en v2, P18.7c).
    """

    tier = etude_ouverte.tier_de(reunion)

    resultat = tier.resume

    if resultat is None:
        raise EtudeError(
            f"Aucun résumé pour la réunion {reunion}"
        )

    for version in resultat.versions:

        if version.numero == numero:

            version.validation = Validation(
                statut="valide",
                horodatage=horodatage_courant(),
                validateur=validateur,
            )

            tier.reunion.resume_valide = True

            etude_ouverte.reunions[
                reunion
            ].resume_valide = True

            etude_ouverte.journal_traitement(
                reunion
            ).ajouter(
                TYPE_VALIDATION,
                fid=None,
                reunion=reunion,
                version=numero,
                resultat=RESULTAT_SUCCES,
                message=(
                    f"Résumé version {numero} validé "
                    f"par {validateur}."
                )
            )

            if etude_ouverte.est_v2():
                sauvegarder_tier(tier)

            return

    raise EtudeError(
        f"Version {numero} introuvable "
        f"pour le résumé de {reunion}"
    )


def devalider_version_resume(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    numero: int
) -> None:
    """
    Dévalide une version du résumé d'une réunion
    (resume_valide redevient False ; le résumé est
    de nouveau modifiable). Une entrée de log
    devalidation est consignée.
    """

    tier = etude_ouverte.tier_de(reunion)

    resultat = tier.resume

    if resultat is None:
        raise EtudeError(
            f"Aucun résumé pour la réunion {reunion}"
        )

    for version in resultat.versions:

        if version.numero == numero:

            version.validation = None

            tier.reunion.resume_valide = False

            etude_ouverte.reunions[
                reunion
            ].resume_valide = False

            etude_ouverte.journal_traitement(
                reunion
            ).ajouter(
                TYPE_DEVALIDATION,
                fid=None,
                reunion=reunion,
                version=numero,
                resultat=RESULTAT_SUCCES,
                message=(
                    f"Résumé version {numero} dévalidé."
                )
            )

            if etude_ouverte.est_v2():
                sauvegarder_tier(tier)

            return

    raise EtudeError(
        f"Version {numero} introuvable "
        f"pour le résumé de {reunion}"
    )


def ajouter_version_synthese(
    etude_ouverte: EtudeOuverte,
    texte: str,
    declencheur: str = "manuel",
    stats: dict = None
) -> VersionSynthese:
    """
    Ajoute une version à la synthèse d'étude
    (niveau étude — surcharge de paramètres de synthèse
    au niveau étude, P18.7e) ; ``stats`` pour l'appel
    LLM ayant produit la version (None sinon).
    """

    numeros = [
        version.numero
        for version in etude_ouverte.synthese.versions
    ]

    version = VersionSynthese(
        numero=max(numeros, default=0) + 1,
        texte=normaliser_sauts_paragraphe(texte),
        horodatage=horodatage_courant(),
        declencheur=declencheur,
    )

    etude_ouverte.synthese.versions.append(version)

    etude_ouverte.journal.ajouter(
        TYPE_SYNTHESE,
        fid=None,
        reunion=None,
        version=version.numero,
        resultat=RESULTAT_SUCCES,
        message=(
            f"Synthèse d'étude version "
            f"{version.numero} ({declencheur})"
        ),
        stats=stats,
        extras={
            "declencheur": declencheur,
        }
    )

    return version


def ouvrir_reunion_autonome(dossier_projet, creer: bool = True):
    """
    Ouvre un projet v1 comme RÉUNION AUTONOME (P18.7d) :
    son tier ``transcriptstudio\\`` porte tous ses
    traitements, sans aucune étude.

    Retourne (EtudeOuverte, nom) — l'EtudeOuverte est une
    vue synthétique v2 à une seule réunion, en
    ``mode_autonome`` : ``sauvegarder_etude`` n'y écrit que
    le tier (aucune écriture hors de ``transcriptstudio\\``
    dans le projet v1).

    ``creer=False`` : ne crée jamais le tier ; retourne
    None s'il n'existe pas.
    """

    dossier_projet = _dossier_projet_v1(
        Path(dossier_projet)
    )

    if not _est_projet_v1(dossier_projet):
        raise EtudeError(
            f"{dossier_projet} n'est pas un projet v1 "
            "(fichier .sttproj attendu)."
        )

    dossier_projet = dossier_projet.resolve()

    tier = ouvrir_tier(dossier_projet)

    if tier is None:

        if not creer:
            return None

        tier = creer_tier(
            dossier_projet,
            nom=dossier_projet.name
        )

    nom = normaliser_nom_fichier(dossier_projet.name)

    if not nom:
        nom = normaliser_nom_fichier("reunion_1")

    maintenant = horodatage_courant()

    etude_ouverte = EtudeOuverte()
    etude_ouverte.mode_autonome = True
    etude_ouverte.dossier = None
    etude_ouverte.etude = Etude(
        etude_format_version=2,
        titre=dossier_projet.name,
        theme="libre",
        gabarit_titre_1="",
        ordre_reunions=[nom],
        creation=maintenant,
        modification=maintenant,
    )

    try:
        from services.avancement import date_audio_projet
        date = date_audio_projet(dossier_projet)
    except Exception:
        date = datetime.now().strftime("%Y-%m-%d")

    etude_ouverte.reunions[nom] = ReunionEtude(
        nom=nom,
        reference=f"{nom}.json",
        chemin_projet=".",
        chemin_absolu=_normaliser_chemin(
            str(dossier_projet)
        ),
        date=date or datetime.now().strftime("%Y-%m-%d"),
        numero=1,
        titre_1="",
        resume_valide=tier.reunion.resume_valide,
    )

    etude_ouverte.tiers[nom] = tier
    etude_ouverte.chemins_resolus[nom] = dossier_projet

    # En autonome, pas de surcharge de synthèse d'étude.
    parametres = parametres_par_defaut()
    parametres.synthese = dict(tier.parametres.synthese)
    etude_ouverte.parametres = parametres

    etude_ouverte.synthese = SyntheseEtude()

    # En autonome, le journal d'étude est celui du tier.
    etude_ouverte.journal = tier.journal

    return etude_ouverte, nom
