# services/tier_reunion.py
"""
Tier réunion (P18.7a) : stockage des traitements au niveau
RÉUNION, dans le projet v1, sous-dossier additif
``transcriptstudio\\`` — aucune autre modification du
projet v1.

Structure exacte (contrat stockage réunions §2) :

    <projet v1>/
    ├── project.sttproj
    ├── journal_operations.json          (prétraitement, inchangé)
    └── transcriptstudio/
        ├── reunion.json                 identité + etudes[] + resume_valide
        ├── blocs/
        │   ├── journal-fid.json         registre FID de LA réunion
        │   └── decoupage.json           segmentation en blocs
        ├── traitements/
        │   ├── reformulation/<FID>.json résultats versionnés par bloc
        │   ├── resume.json              résumé versionné de la réunion
        │   └── journal_operations.json  log des opérations de la réunion
        └── parametres/
            └── parametres.json          paramètres des traitements de la réunion

Règles de fond (P18.7) :
- identité de bloc = (réunion, FID) : le registre FID est
  PAR RÉUNION (le registre global d'étude est abrogé pour
  les nouvelles données) ;
- toute opération sur les traitements de la réunion, où
  qu'elle soit lancée, utilise les paramètres DU TIER ;
- aucune écriture en retour : ni l'étude, ni l'ouvrage
  n'écrivent jamais dans le tier — seules les opérations sur
  les traitements de la réunion y écrivent ;
- le rattachement est un héritage total silencieux (la
  réunion garde tout son travail) et le détachement est non
  destructif.
"""

import json
import os
from pathlib import Path

from models.etude import (
    DecoupageReunion,
    ParametresEtude,
    RegistreFID,
    ReunionTier,
    ResultatReformulation,
    ResultatResume,
)
from services.etude_schema import (
    EtudeFormatError,
    valider_decoupage,
    valider_parametres,
    valider_reformulation,
    valider_registre_fid,
    valider_reunion_tier,
    valider_resume,
)
from services.timecodes import horodatage_iso
from services.traitements.journal import (
    FICHIER_JOURNAL,
    JournalEtude,
)


DOSSIER_TIER = "transcriptstudio"

FICHIER_REUNION = "reunion.json"

DOSSIER_BLOCS = "blocs"
FICHIER_REGISTRE_FID = "journal-fid.json"
FICHIER_DECOUPAGE = "decoupage.json"

DOSSIER_TRAITEMENTS = "traitements"
DOSSIER_REFORMULATION = "reformulation"
FICHIER_RESUME = "resume.json"

DOSSIER_PARAMETRES = "parametres"
FICHIER_PARAMETRES = "parametres.json"


class TierError(Exception):
    """
    Erreur de manipulation d'un tier réunion (dossier
    projet illisible, fichier de tier invalide...).
    """

    pass


def _ecrire_json(chemin: Path, data: dict) -> None:

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

    with open(
        chemin,
        "r",
        encoding="utf-8"
    ) as fichier:
        return json.load(fichier)


def _normaliser_chemin(chemin: str) -> str:

    if chemin is None:
        return None

    return str(chemin).replace("\\", "/")


def chemin_tier(dossier_projet) -> Path:
    """
    Chemin du sous-dossier ``transcriptstudio\\`` d'un
    projet v1.
    """

    return Path(dossier_projet) / DOSSIER_TIER


def tier_existe(dossier_projet) -> bool:
    """
    Le projet v1 porte-t-il déjà un tier réunion ?
    """

    return (
        chemin_tier(dossier_projet)
        / FICHIER_REUNION
    ).is_file()


def _chemin_etude_relatif(
    dossier_projet: Path,
    dossier_etude: Path
) -> str:
    """
    Chemin de l'étude relatif au dossier du projet v1
    quand possible (portabilité), absolu sinon.
    """

    try:

        return _normaliser_chemin(
            os.path.relpath(
                str(Path(dossier_etude).resolve()),
                str(Path(dossier_projet).resolve())
            )
        )

    except (ValueError, OSError):
        # Lecteurs différents (Windows) : absolu.
        return _normaliser_chemin(
            str(Path(dossier_etude).resolve())
        )


class TierReunion:
    """
    Le tier d'une réunion : tout son travail de traitements,
    stocké dans le projet v1 (``transcriptstudio\\``).

    - ``reunion`` : identité (``reunion.json``) ;
    - ``registre`` : registre FID DE LA RÉUNION (P18.7b) ;
    - ``decoupage`` : segmentation en blocs (None si aucune) ;
    - ``reformulations`` : {FID -> ResultatReformulation} ;
    - ``resume`` : ResultatResume ou None ;
    - ``parametres`` : paramètres des traitements de la
      réunion (P18.7e) ;
    - ``journal`` : log des opérations de la réunion.
    """

    def __init__(self, dossier_projet):

        self.dossier_projet: Path = Path(dossier_projet)
        self.reunion: ReunionTier = None
        self.registre: RegistreFID = RegistreFID()
        self.decoupage: DecoupageReunion = None
        self.reformulations: dict = {}
        self.resume: ResultatResume = None
        self.parametres: ParametresEtude = None
        self.journal: JournalEtude = None

    @property
    def dossier(self) -> Path:
        return chemin_tier(self.dossier_projet)

    @property
    def nom(self) -> str:
        return (
            self.reunion.nom
            if self.reunion is not None
            else self.dossier_projet.name
        )

    def enregistrer_etude(
        self,
        dossier_etude,
        ajouter: bool = True
    ) -> None:
        """
        Enregistre (ou retire) une étude dans ``etudes[]``
        du tier — sans jamais toucher au reste du travail
        de la réunion (détachement non destructif).
        """

        chemin = _chemin_etude_relatif(
            self.dossier_projet,
            Path(dossier_etude)
        )

        if ajouter:

            if chemin not in self.reunion.etudes:
                self.reunion.etudes.append(chemin)

        else:

            while chemin in self.reunion.etudes:
                self.reunion.etudes.remove(chemin)

        self.reunion.modification = horodatage_iso()

        sauvegarder_reunion_tier(self)


def creer_tier(
    dossier_projet,
    nom: str = None,
    parametres: ParametresEtude = None
) -> TierReunion:
    """
    Crée le tier d'un projet v1 (structure exacte §2).

    Additif : ne modifie aucun fichier existant du projet
    v1 hors ``transcriptstudio\\``. Refuse si un fichier
    occupe l'emplacement d'un sous-dossier du tier.
    """

    dossier_projet = Path(dossier_projet)

    tier = TierReunion(dossier_projet)

    fichiers_tier = (
        FICHIER_REUNION,
        f"{DOSSIER_BLOCS}/{FICHIER_REGISTRE_FID}",
        f"{DOSSIER_BLOCS}/{FICHIER_DECOUPAGE}",
        f"{DOSSIER_TRAITEMENTS}/{FICHIER_RESUME}",
        f"{DOSSIER_TRAITEMENTS}/{FICHIER_JOURNAL}",
        f"{DOSSIER_PARAMETRES}/{FICHIER_PARAMETRES}",
    )

    for relatif in fichiers_tier:

        chemin = tier.dossier / relatif

        if chemin.exists() and not chemin.is_file():
            raise TierError(
                f"{chemin} existe et n'est pas un "
                "fichier : le tier ne peut pas être "
                "créé ici."
            )

    #
    # Le dossier reformulation/ existe dès la création
    # (structure exacte §2), même vide.
    #

    (
        tier.dossier
        / DOSSIER_TRAITEMENTS
        / DOSSIER_REFORMULATION
    ).mkdir(parents=True, exist_ok=True)

    if (tier.dossier / FICHIER_REUNION).exists():
        raise TierError(
            f"Le projet {dossier_projet} a déjà un "
            "tier réunion (transcriptstudio/"
            f"{FICHIER_REUNION}) : il ne s'écrase "
            "pas."
        )

    maintenant = horodatage_iso()

    tier.reunion = ReunionTier(
        nom=nom or dossier_projet.name,
        etudes=[],
        resume_valide=False,
        creation=maintenant,
        modification=maintenant,
    )

    tier.registre = RegistreFID()

    if parametres is None:

        # Import tardif : etude_io importe ce module.
        from services.etude_io import (
            parametres_par_defaut,
        )

        parametres = parametres_par_defaut()

    tier.parametres = parametres

    tier.journal = JournalEtude(
        tier.dossier
        / DOSSIER_TRAITEMENTS
        / FICHIER_JOURNAL
    )

    sauvegarder_tier(tier)

    tier.journal.initialiser()

    return tier


def ouvrir_tier(dossier_projet) -> TierReunion:
    """
    Ouvre le tier d'un projet v1.

    Retourne None si le projet n'a pas de tier. Lève
    EtudeFormatError si un fichier du tier viole le schéma.
    """

    dossier_projet = Path(dossier_projet)

    fichier_reunion = (
        chemin_tier(dossier_projet) / FICHIER_REUNION
    )

    if not fichier_reunion.is_file():
        return None

    tier = TierReunion(dossier_projet)

    donnees = _lire_json(fichier_reunion)
    valider_reunion_tier(donnees, str(fichier_reunion))
    tier.reunion = ReunionTier.from_dict(donnees)

    #
    # Registre FID de la réunion.
    #

    chemin_registre = (
        tier.dossier
        / DOSSIER_BLOCS
        / FICHIER_REGISTRE_FID
    )

    if chemin_registre.exists():

        donnees = _lire_json(chemin_registre)
        valider_registre_fid(donnees, str(chemin_registre))
        tier.registre = RegistreFID.from_dict(donnees)

    #
    # Découpage.
    #

    chemin_decoupage = (
        tier.dossier
        / DOSSIER_BLOCS
        / FICHIER_DECOUPAGE
    )

    if chemin_decoupage.exists():

        donnees = _lire_json(chemin_decoupage)
        valider_decoupage(donnees, str(chemin_decoupage))
        tier.decoupage = DecoupageReunion.from_dict(
            donnees
        )

    #
    # Reformulations (par FID de la réunion).
    #

    dossier_reformulation = (
        tier.dossier
        / DOSSIER_TRAITEMENTS
        / DOSSIER_REFORMULATION
    )

    if dossier_reformulation.is_dir():

        for chemin in sorted(
            dossier_reformulation.glob("*.json")
        ):

            donnees = _lire_json(chemin)
            valider_reformulation(donnees, str(chemin))

            resultat = ResultatReformulation.from_dict(
                donnees
            )

            tier.reformulations[resultat.fid] = resultat

    #
    # Résumé.
    #

    chemin_resume = (
        tier.dossier
        / DOSSIER_TRAITEMENTS
        / FICHIER_RESUME
    )

    if chemin_resume.exists():

        donnees = _lire_json(chemin_resume)
        valider_resume(donnees, str(chemin_resume))
        tier.resume = ResultatResume.from_dict(donnees)

    #
    # Paramètres du tier.
    #

    chemin_parametres = (
        tier.dossier
        / DOSSIER_PARAMETRES
        / FICHIER_PARAMETRES
    )

    if chemin_parametres.exists():

        donnees = _lire_json(chemin_parametres)
        valider_parametres(
            donnees,
            str(chemin_parametres)
        )

        tier.parametres = ParametresEtude.from_dict(
            donnees
        )

    else:

        from services.etude_io import (
            parametres_par_defaut,
        )

        tier.parametres = parametres_par_defaut()

    #
    # Journal des opérations de la réunion.
    #

    tier.journal = JournalEtude(
        tier.dossier
        / DOSSIER_TRAITEMENTS
        / FICHIER_JOURNAL
    )

    return tier


def sauvegarder_reunion_tier(tier: TierReunion) -> None:
    """
    Écrit ``reunion.json`` du tier (identité, etudes[],
    resume_valide).
    """

    _ecrire_json(
        tier.dossier / FICHIER_REUNION,
        tier.reunion.to_dict()
    )


def sauvegarder_tier(tier: TierReunion) -> None:
    """
    Écrit l'intégralité du tier sur disque.

    Seuls les fichiers du tier sont écrits : jamais aucun
    autre fichier du projet v1.
    """

    sauvegarder_reunion_tier(tier)

    _ecrire_json(
        tier.dossier
        / DOSSIER_BLOCS
        / FICHIER_REGISTRE_FID,
        tier.registre.to_dict()
    )

    if tier.decoupage is not None:
        _ecrire_json(
            tier.dossier
            / DOSSIER_BLOCS
            / FICHIER_DECOUPAGE,
            tier.decoupage.to_dict()
        )

    for resultat in tier.reformulations.values():
        _ecrire_json(
            tier.dossier
            / DOSSIER_TRAITEMENTS
            / DOSSIER_REFORMULATION
            / f"{resultat.fid}.json",
            resultat.to_dict()
        )

    if tier.resume is not None:
        _ecrire_json(
            tier.dossier
            / DOSSIER_TRAITEMENTS
            / FICHIER_RESUME,
            tier.resume.to_dict()
        )

    if tier.parametres is not None:
        _ecrire_json(
            tier.dossier
            / DOSSIER_PARAMETRES
            / FICHIER_PARAMETRES,
            tier.parametres.to_dict()
        )

    #
    # Le journal s'écrit lui-même à chaque opération
    # (append-only, survie aux crashes) ; on le crée
    # s'il manque encore.
    #

    if tier.journal is not None:
        tier.journal.initialiser()