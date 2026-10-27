# services/etude_io.py
"""
Lecture, écriture et manipulation d'une étude v2 (P14.1).

Le dossier étude (contrat CONTRAT_FORMAT_ETUDE_V2.md §2) :

    Etude_Luc/
    ├── etude.json                     contrat de l'étude
    ├── reunions/<nom>.json            références aux projets v1
    ├── blocs/journal-fid.json         registre FID (unique pour l'étude)
    ├── blocs/decoupage/<reunion>.json segmentation d'une réunion
    ├── traitements/reformulation/<FID>.json   résultats versionnés par bloc
    ├── traitements/resume/<reunion>.json      résumés versionnés par réunion
    ├── synthese/synthese.json         synthèse d'étude versionnée
    └── parametres/parametres.json     réglages de l'étude

Règles de fond :
- ouvrir ou manipuler une étude ne modifie jamais un projet
  v1 référencé (règle d'invariance 1) ;
- un FID, une fois attribué, désigne pour toujours le même
  discours ; les versions ne s'écrasent pas (règle 2) ;
- retirer une réunion retire sa référence et ses résultats
  d'étude, mais ne touche ni le projet v1 ni le registre
  FID (règle 3) ;
- les chemins se résolvent par ordre relatif, puis absolu,
  puis relocalisation guidée (règle 4) ;
- un projet v1 peut être référencé par plusieurs études
  simultanément (règle 5).

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
    valider_registre_fid,
    valider_reformulation,
    valider_reunion,
    valider_resume,
    valider_synthese,
)
from services.resources import resource_path
from services.timecodes import horodatage_iso


FICHIER_ETUDE = "etude.json"

DOSSIER_REUNIONS = "reunions"
DOSSIER_BLOCS = "blocs"
DOSSIER_DECOUPAGE = "decoupage"
DOSSIER_TRAITEMENTS = "traitements"
DOSSIER_REFORMULATION = "reformulation"
DOSSIER_RESUME = "resume"
DOSSIER_SYNTHESE = "synthese"
DOSSIER_PARAMETRES = "parametres"

FICHIER_REGISTRE_FID = "journal-fid.json"
FICHIER_SYNTHESE = "synthese.json"
FICHIER_PARAMETRES = "parametres.json"


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


def _lire_prompt_par_defaut(nom_fichier: str) -> str:
    """
    Charge un prompt v2 de référence embarqué dans
    l'application (valeur par défaut des paramètres).
    """

    chemin = resource_path(
        f"resources/prompts/{nom_fichier}"
    )

    with open(
        chemin,
        "r",
        encoding="utf-8"
    ) as fichier:
        return fichier.read().strip()


def parametres_par_defaut() -> ParametresEtude:
    """
    Paramètres initiaux d'une étude (contrat §10) :
    prompts v2 de référence intégrés comme valeurs
    actives, aucun secret (CredentialStore v1).
    """

    return ParametresEtude(
        reformulation={
            "prompt": _lire_prompt_par_defaut(
                "prompt_reformulation_v2.md"
            ),
            "modele": "mistral-large-latest",
            "fenetre_glissante_tokens": 2000,
        },
        resume={
            "prompt": _lire_prompt_par_defaut(
                "prompt_resume_v2.md"
            ),
            "modele": "mistral-large-latest",
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
    )


class EtudeOuverte:
    """
    Une étude chargée en mémoire, avec l'état de
    résolution de ses réunions.

    ``reunions_introuvables`` liste les réunions dont le
    projet v1 est introuvable (mode dégradé : elles
    n'empêchent pas l'ouverture des autres).
    """

    def __init__(self):

        self.dossier: Path = None
        self.etude: Etude = None
        self.registre: RegistreFID = None
        self.parametres: ParametresEtude = None
        self.synthese: SyntheseEtude = None

        self.reunions: dict = {}
        self.decoupages: dict = {}
        self.reformulations: dict = {}
        self.resumes: dict = {}

        self.reunions_introuvables: list = []

        # Chemin du projet v1 résolu pour chaque réunion
        # joignable (None sinon).
        self.chemins_resolus: dict = {}

    def reunion_joignable(self, nom: str) -> bool:
        """
        La réunion est-elle joignable (projet v1
        résolu) ?
        """

        return (
            nom in self.chemins_resolus
            and self.chemins_resolus[nom] is not None
        )


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
    )
) -> EtudeOuverte:
    """
    Crée le dossier étude et sa structure complète.

    Le dossier doit être vide ou inexistant : jamais
    d'écrasement silencieux.
    """

    dossier = Path(dossier)

    if dossier.exists() and any(dossier.iterdir()):
        raise EtudeError(
            f"Le dossier {dossier} n'est pas vide ; "
            "une étude ne s'y crée pas."
        )

    dossier.mkdir(parents=True, exist_ok=True)

    for sous_dossier in (
        DOSSIER_REUNIONS,
        f"{DOSSIER_BLOCS}/{DOSSIER_DECOUPAGE}",
        f"{DOSSIER_TRAITEMENTS}/{DOSSIER_REFORMULATION}",
        f"{DOSSIER_TRAITEMENTS}/{DOSSIER_RESUME}",
        DOSSIER_SYNTHESE,
        DOSSIER_PARAMETRES,
    ):
        (dossier / sous_dossier).mkdir(
            parents=True,
            exist_ok=True
        )

    maintenant = horodatage_courant()

    etude_ouverte = EtudeOuverte()

    etude_ouverte.dossier = dossier
    etude_ouverte.etude = Etude(
        etude_format_version=1,
        titre=titre,
        theme=theme,
        gabarit_titre_1=gabarit_titre_1,
        ordre_reunions=[],
        creation=maintenant,
        modification=maintenant,
    )

    etude_ouverte.registre = RegistreFID()
    etude_ouverte.parametres = parametres_par_defaut()
    etude_ouverte.synthese = SyntheseEtude()

    sauvegarder_etude(etude_ouverte)

    return etude_ouverte


def sauvegarder_etude(etude_ouverte: EtudeOuverte) -> None:
    """
    Écrit l'intégralité de l'étude sur disque.

    Seuls les fichiers de l'étude sont écrits : jamais
    un projet v1 référencé (règle d'invariance 1).
    """

    dossier = etude_ouverte.dossier

    if dossier is None or etude_ouverte.etude is None:
        raise EtudeError(
            "Étude non initialisée : rien à sauvegarder."
        )

    etude_ouverte.etude.modification = (
        horodatage_courant()
    )

    _ecrire_json(
        dossier / FICHIER_ETUDE,
        etude_ouverte.etude.to_dict()
    )

    for nom, reunion in etude_ouverte.reunions.items():
        _ecrire_json(
            dossier / DOSSIER_REUNIONS
            / f"{nom}.json",
            reunion.to_dict()
        )

    _ecrire_json(
        dossier / DOSSIER_BLOCS
        / FICHIER_REGISTRE_FID,
        etude_ouverte.registre.to_dict()
    )

    for decoupage in (
        etude_ouverte.decoupages.values()
    ):
        _ecrire_json(
            dossier / DOSSIER_BLOCS
            / DOSSIER_DECOUPAGE
            / f"{decoupage.reunion}.json",
            decoupage.to_dict()
        )

    for resultat in (
        etude_ouverte.reformulations.values()
    ):
        _ecrire_json(
            dossier / DOSSIER_TRAITEMENTS
            / DOSSIER_REFORMULATION
            / f"{resultat.fid}.json",
            resultat.to_dict()
        )

    for resultat in etude_ouverte.resumes.values():
        _ecrire_json(
            dossier / DOSSIER_TRAITEMENTS
            / DOSSIER_RESUME
            / f"{resultat.reunion}.json",
            resultat.to_dict()
        )

    _ecrire_json(
        dossier / DOSSIER_SYNTHESE
        / FICHIER_SYNTHESE,
        etude_ouverte.synthese.to_dict()
    )

    _ecrire_json(
        dossier / DOSSIER_PARAMETRES
        / FICHIER_PARAMETRES,
        etude_ouverte.parametres.to_dict()
    )


def ouvrir_etude(dossier) -> EtudeOuverte:
    """
    Ouvre une étude existante.

    Chaque réunion est résolue par ordre : chemin relatif
    au dossier étude, puis chemin absolu historique ; une
    réunion introuvable place l'étude en mode dégradé sans
    bloquer les autres.

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

    etude_ouverte = EtudeOuverte()
    etude_ouverte.dossier = dossier

    donnees = _lire_json(fichier_etude)
    valider_etude(donnees, str(fichier_etude))
    etude_ouverte.etude = Etude.from_dict(donnees)

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
    # Registre FID.
    #

    chemin_registre = (
        dossier / DOSSIER_BLOCS
        / FICHIER_REGISTRE_FID
    )

    if chemin_registre.exists():

        donnees_registre = _lire_json(chemin_registre)
        valider_registre_fid(
            donnees_registre,
            str(chemin_registre)
        )

        etude_ouverte.registre = (
            RegistreFID.from_dict(donnees_registre)
        )

    else:
        etude_ouverte.registre = RegistreFID()

    #
    # Découpages existants.
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

            etude_ouverte.decoupages[
                decoupage.reunion
            ] = decoupage

    #
    # Résultats de reformulation (par FID).
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

            etude_ouverte.reformulations[
                resultat.fid
            ] = resultat

    #
    # Résumés (par réunion).
    #

    dossier_resume = (
        dossier / DOSSIER_TRAITEMENTS
        / DOSSIER_RESUME
    )

    if dossier_resume.exists():

        for chemin in sorted(dossier_resume.glob("*.json")):

            donnees = _lire_json(chemin)
            valider_resume(donnees, str(chemin))

            resultat = ResultatResume.from_dict(donnees)

            etude_ouverte.resumes[
                resultat.reunion
            ] = resultat

    #
    # Synthèse d'étude.
    #

    chemin_synthese = (
        dossier / DOSSIER_SYNTHESE / FICHIER_SYNTHESE
    )

    if chemin_synthese.exists():

        donnees = _lire_json(chemin_synthese)
        valider_synthese(donnees, str(chemin_synthese))

        etude_ouverte.synthese = (
            SyntheseEtude.from_dict(donnees)
        )

    else:
        etude_ouverte.synthese = SyntheseEtude()

    #
    # Paramètres.
    #

    chemin_parametres = (
        dossier / DOSSIER_PARAMETRES
        / FICHIER_PARAMETRES
    )

    if chemin_parametres.exists():

        donnees = _lire_json(chemin_parametres)
        valider_parametres(
            donnees,
            str(chemin_parametres)
        )

        etude_ouverte.parametres = (
            ParametresEtude.from_dict(donnees)
        )

    else:
        etude_ouverte.parametres = parametres_par_defaut()

    #
    # Résolution des réunions : relatif, puis absolu,
    # puis mode dégradé.
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

    return etude_ouverte


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
        resume_valide=False,
    )

    etude_ouverte.reunions[nom] = reunion
    etude_ouverte.chemins_resolus[nom] = dossier_projet

    etude_ouverte.etude.ordre_reunions.append(nom)

    return nom


def retirer_reunion(
    etude_ouverte: EtudeOuverte,
    nom: str
) -> None:
    """
    Retire une réunion de l'étude : sa référence et ses
    résultats d'étude disparaissent (découpage, résumé,
    reformulations de ses FIDs).

    Le projet v1 n'est jamais touché, pas plus que le
    registre FID (règle d'invariance 3).
    """

    if nom not in etude_ouverte.reunions:
        raise EtudeError(f"Réunion inconnue : {nom}")

    dossier = etude_ouverte.dossier

    etude_ouverte.reunions.pop(nom)
    etude_ouverte.chemins_resolus.pop(nom, None)

    if nom in etude_ouverte.reunions_introuvables:
        etude_ouverte.reunions_introuvables.remove(nom)

    etude_ouverte.etude.ordre_reunions.remove(nom)

    etude_ouverte.decoupages.pop(nom, None)
    etude_ouverte.resumes.pop(nom, None)

    fids = [
        fid
        for fid, entree
        in etude_ouverte.registre.entrees.items()
        if entree.reunion == nom
    ]

    for fid in fids:
        etude_ouverte.reformulations.pop(fid, None)

    #
    # Fichiers de résultats retirés (la référence, le
    # découpage, le résumé et les reformulations) ;
    # le registre FID reste intact.
    #

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

    Le FID est un entier séquentiel, jamais réutilisé :
    prochain_fid avance même après suppression ou fusion
    (règle d'invariance 2).
    """

    fid = etude_ouverte.registre.prochain_fid

    etude_ouverte.registre.prochain_fid = fid + 1

    etude_ouverte.registre.entrees[fid] = EntreeFID(
        fid=fid,
        reunion=reunion,
        cree=horodatage_courant(),
        actif=True,
        fin=None,
    )

    return fid


def marquer_fid_inactif(
    etude_ouverte: EtudeOuverte,
    fid: int
) -> None:
    """
    Marque un FID comme inactif (bloc supprimé ou
    fusionné). Le FID reste au registre, les résultats
    associés aussi.
    """

    entree = etude_ouverte.registre.entrees.get(fid)

    if entree is None:
        raise EtudeError(f"FID inconnu : {fid}")

    entree.actif = False
    entree.fin = horodatage_courant()


def enregistrer_decoupage(
    etude_ouverte: EtudeOuverte,
    decoupage: DecoupageReunion
) -> None:
    """
    Enregistre la segmentation d'une réunion.

    Chaque bloc doit porter un FID attribué du registre
    et appartenir à la réunion ; le texte source est
    immuable après enregistrement.
    """

    if decoupage.reunion not in etude_ouverte.reunions:
        raise EtudeError(
            f"Réunion inconnue : {decoupage.reunion}"
        )

    for bloc in decoupage.blocs:

        entree = etude_ouverte.registre.entrees.get(
            bloc.fid
        )

        if entree is None:
            raise EtudeError(
                f"FID {bloc.fid} absent du registre"
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

    etude_ouverte.decoupages[
        decoupage.reunion
    ] = decoupage


def ajouter_version_reformulation(
    etude_ouverte: EtudeOuverte,
    fid: int,
    texte: str,
    type_version: str = "passe",
    consigne: str = None,
    selection: dict = None,
    stats: dict = None,
    contexte: list = None
) -> VersionReformulation:
    """
    Ajoute une version au résultat de reformulation d'un
    bloc. L'historique est complet : jamais d'écrasement
    (règle d'invariance 2).
    """

    if fid not in etude_ouverte.registre.entrees:
        raise EtudeError(f"FID inconnu : {fid}")

    resultat = etude_ouverte.reformulations.get(fid)

    if resultat is None:
        resultat = ResultatReformulation(fid=fid)
        etude_ouverte.reformulations[fid] = resultat

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
        contexte=list(contexte or []),
    )

    resultat.versions.append(version)

    return version


def valider_version_reformulation(
    etude_ouverte: EtudeOuverte,
    fid: int,
    numero: int,
    validateur: str
) -> None:
    """
    Valide une version précise du résultat d'un bloc :
    la validation se porte sur la version, qui devient
    la version figée du bloc.
    """

    resultat = etude_ouverte.reformulations.get(fid)

    if resultat is None:
        raise EtudeError(
            f"Aucun résultat de reformulation "
            f"pour le FID {fid}"
        )

    for version in resultat.versions:

        if version.numero == numero:

            version.validation = Validation(
                statut="valide",
                horodatage=horodatage_courant(),
                validateur=validateur,
            )

            return

    raise EtudeError(
        f"Version {numero} introuvable "
        f"pour le FID {fid}"
    )


def ajouter_version_resume(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    texte: str,
    source: str
) -> VersionResume:
    """
    Ajoute une version au résumé d'une réunion. La
    source utilisée est stockée avec le résultat.
    """

    if reunion not in etude_ouverte.reunions:
        raise EtudeError(f"Réunion inconnue : {reunion}")

    resultat = etude_ouverte.resumes.get(reunion)

    if resultat is None:
        resultat = ResultatResume(reunion=reunion)
        etude_ouverte.resumes[reunion] = resultat

    numeros = [
        version.numero
        for version in resultat.versions
    ]

    version = VersionResume(
        numero=max(numeros, default=0) + 1,
        texte=normaliser_sauts_paragraphe(texte),
        source=source,
        horodatage=horodatage_courant(),
        validation=None,
    )

    resultat.versions.append(version)

    return version


def valider_version_resume(
    etude_ouverte: EtudeOuverte,
    reunion: str,
    numero: int,
    validateur: str
) -> None:
    """
    Valide une version précise du résumé d'une réunion
    (resume_valide devient True pour la réunion).
    """

    resultat = etude_ouverte.resumes.get(reunion)

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

            etude_ouverte.reunions[
                reunion
            ].resume_valide = True

            return

    raise EtudeError(
        f"Version {numero} introuvable "
        f"pour le résumé de {reunion}"
    )


def ajouter_version_synthese(
    etude_ouverte: EtudeOuverte,
    texte: str,
    declencheur: str = "manuel"
) -> VersionSynthese:
    """
    Ajoute une version à la synthèse d'étude
    (déclencheur : validation de bloc, manuel, ou
    création de l'étude).
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

    return version
