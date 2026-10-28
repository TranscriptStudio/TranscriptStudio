# services/bibles.py
"""
Téléchargeur et gestion des Bibles OSIS (P18.5 —
spec BIBLE_JND_V2_2026-10-28b.md, fait autorité).

Versions supportées (spec §1) :

| Identifiant | Version | Source OSIS | Licence |
|---|---|---|---|
| darby | Bible J. N. Darby (éd. 2024, rév. 2.0) | concordance.bible (miroir BPC), zip OSIS | Domaine public |
| darbyR | Bible J. N. Darby révisée (éd. 2026, rév. 2.3) | concordance.bible (miroir BPC), zip OSIS | CC BY NC ND |
| segond1910 | Segond 1910 | lien direct NON vérifié (2026-10-28) → import manuel | Domaine public |

Règles de fond :
- les fichiers Bible ne sont **jamais commités**
  (poids + licences) : stockés dans le dossier de
  ressources de l'app, hors périmètre git (.gitignore) ;
- **aucun téléchargement silencieux** : toujours à
  la demande depuis les réglages « Bibles » ;
- un téléchargement interrompu ne laisse **aucun
  fichier partiel** (téléchargement en .part,
  validation, puis installation atomique) ;
- **version retenue par étude** : bloc `bible` de
  `parametres/parametres.json`, défaut `darbyR`
  (décision David 2026-10-28) — sans migration pour
  les études existantes (absence de bloc = défaut) ;
- versifications différentes : un écart est une
  **information consultable** dans les autres
  versions installées, jamais une décision
  automatique.
"""

import shutil
import urllib.request
import zipfile
from pathlib import Path

from services.resources import resource_path


class ErreurBible(Exception):
    """
    Erreur explicite du gestionnaire de Bibles
    (réseau, fichier invalide, version inconnue).
    """


#
# Catalogue des versions (spec §1).
#

VERSIONS_BIBLE = {
    "darby": {
        "identifiant": "darby",
        "nom": "Bible — Traduction J. N. Darby",
        "editeur": "Bibles et Publications Chrétiennes",
        "edition": "Édition 2024 (rév. 2.0)",
        "licence": "Domaine public",
        "fichier": "Darby.osis.xml",
        "url_zip": (
            "https://concordance.bible/media/"
            "download/Darby-osis.zip"
        ),
        "page_source": (
            "https://editeurbpc.com/telechargements"
        ),
    },
    "darbyR": {
        "identifiant": "darbyR",
        "nom": "Bible — Traduction J. N. Darby révisée",
        "editeur": "Bibles et Publications Chrétiennes",
        "edition": "Édition 2026 (rév. 2.3)",
        "licence": "CC BY NC ND",
        "fichier": "DarbyR.osis.xml",
        "url_zip": (
            "https://concordance.bible/media/"
            "download/DarbyR-osis.zip"
        ),
        "page_source": (
            "https://editeurbpc.com/telechargements"
        ),
    },
    "segond1910": {
        "identifiant": "segond1910",
        "nom": "Bible — Segond 1910",
        "editeur": "concordance.bible",
        "edition": "Segond 1910",
        "licence": "Domaine public",
        "fichier": "Segond1910.osis.xml",
        #
        # Aucun lien OSIS direct vérifié (2026-10-28) :
        # import manuel (« Charger depuis un
        # fichier… »), conformément à la spec §1.
        #
        "url_zip": None,
        "page_source": "https://concordance.bible",
    },
}

VERSION_BIBLE_DEFAUT = "darbyR"

_TAILLE_BLOC = 64 * 1024


def dossier_bibles(dossier=None) -> Path:
    """
    Dossier de stockage des Bibles (dossier de
    ressources de l'app, hors dépôt git —
    injectable pour les tests).
    """

    if dossier is not None:
        return Path(dossier)

    return resource_path("resources/bible")


def chemin_version(identifiant: str, dossier=None) -> Path:
    """
    Chemin du fichier OSIS d'une version.
    """

    version = VERSIONS_BIBLE.get(identifiant)

    if version is None:
        raise ErreurBible(
            f"Version de Bible inconnue : {identifiant}"
        )

    return (
        dossier_bibles(dossier) / version["fichier"]
    )


def version_installee(identifiant: str, dossier=None) -> bool:
    """
    La version est-elle installée ?
    """

    try:
        return chemin_version(
            identifiant,
            dossier
        ).is_file()
    except ErreurBible:
        return False


def versions_installees(dossier=None) -> list:
    """
    Identifiants des versions installées.
    """

    return [
        identifiant
        for identifiant in VERSIONS_BIBLE
        if version_installee(
            identifiant,
            dossier
        )
    ]


#
# Version retenue par étude (spec §3).
#

def version_bible_etude(parametres) -> str:
    """
    Version de Bible retenue par une étude : bloc
    ``bible`` de parametres.json, défaut ``darbyR``
    (spéc. §3) — une étude existante sans bloc
    s'ouvre sans migration et utilise le défaut ;
    une version inconnue retombe aussi sur le
    défaut (jamais d'erreur bloquante).
    """

    bloc = getattr(parametres, "bible", None)

    if not bloc:
        bloc = {}

    version = bloc.get("version")

    if version in VERSIONS_BIBLE:
        return version

    return VERSION_BIBLE_DEFAUT


def charger_bible_version(
    identifiant: str,
    dossier=None
):
    """
    BibleJND d'une version installée (None si la
    version n'est pas installée).
    """

    if not version_installee(identifiant, dossier):
        return None

    from services.jnd import charger_bible

    try:
        return charger_bible(
            chemin_version(identifiant, dossier)
        )
    except Exception as e:
        raise ErreurBible(
            f"Bible {identifiant} illisible : {e}"
        )


def bible_de_l_etude(
    etude_ouverte,
    parametres=None,
    dossier=None
):
    """
    Bible de la version retenue par l'étude (spec
    §3.3 : le contrôle qualité travaille TOUJOURS
    contre la version de l'étude, jamais une
    version implicite). None si la version n'est
    pas installée.
    """

    if parametres is None:
        parametres = getattr(
            etude_ouverte,
            "parametres",
            None
        )

    identifiant = version_bible_etude(parametres)

    return charger_bible_version(
        identifiant,
        dossier
    )


def autres_versions_installees(
    identifiant_retenu: str,
    dossier=None
) -> dict:
    """
    Autres versions installées (versifications
    différentes, spec §4) : ``{identifiant,
    BibleJND}`` — pour la CONSULTATION d'un écart,
    jamais pour décider à la place de
    l'utilisateur.
    """

    autres = {}

    for identifiant in versions_installees(dossier):

        if identifiant == identifiant_retenu:
            continue

        bible = charger_bible_version(
            identifiant,
            dossier
        )

        if bible is not None:
            autres[identifiant] = bible

    return autres


#
# Validation minimale (spec §2.6).
#

def valider_fichier_bible(chemin) -> tuple:
    """
    Validation minimale d'un fichier OSIS :
    lisible par le chargeur, au moins un livre et
    un verset. Retour (ok, message).
    """

    from services.jnd import (
        BibleAbsente,
        charger_bible,
    )

    try:
        bible = charger_bible(chemin)
    except BibleAbsente:
        return False, (
            "Fichier introuvable."
        )
    except Exception as e:
        return False, (
            f"Fichier OSIS illisible : {e}"
        )

    if not bible.versets:
        return False, (
            "Aucun verset trouvé dans ce fichier "
            "OSIS."
        )

    return True, f"{len(bible.versets)} livre(s)"


#
# Installation (import manuel ou après
# téléchargement) — jamais dans le dépôt git ni
# dans un dossier d'étude (règle 1).
#

def installer_fichier(
    identifiant: str,
    source,
    dossier=None
) -> Path:
    """
    Installe un fichier OSIS (déjà téléchargé par
    l'utilisateur, spec §2.4) comme version donnée :
    validation minimale, copie ATOMIQUE dans le
    dossier des Bibles — rien n'est écrit ailleurs,
    aucun fichier partiel exploitable en cas
    d'échec.
    """

    source = Path(source)

    if not source.is_file():
        raise ErreurBible(
            f"Fichier introuvable : {source}"
        )

    ok, message = valider_fichier_bible(source)

    if not ok:
        raise ErreurBible(
            f"Fichier OSIS invalide — {message}"
        )

    cible = chemin_version(identifiant, dossier)

    cible.parent.mkdir(parents=True, exist_ok=True)

    provisoire = cible.with_suffix(
        cible.suffix + ".part"
    )

    try:
        shutil.copyfile(source, provisoire)

        provisoire.replace(cible)

    except Exception as e:

        provisoire.unlink(missing_ok=True)

        raise ErreurBible(
            f"Installation impossible : {e}"
        )

    return cible


#
# Téléchargement (spec §2.2 : à la demande,
# progression, aucune trace en cas d'échec).
#

def telecharger_bible(
    identifiant: str,
    progression=None,
    annulation=None,
    dossier=None
) -> Path:
    """
    Télécharge la version depuis le site de
    l'éditeur (zip OSIS), l'extrait, le valide,
    puis l'installe atomiquement.

    - ``progression`` : appelé avec (octets lus,
      total) — total None si inconnu ;
    - ``annulation`` : appelé régulièrement ;
      truthy = interruption demandée ;
    - en cas d'erreur réseau, d'annulation ou
      d'invalidité : AUCUN fichier partiel conservé
      (règle 4) et aucune installation.

    Version sans URL directe (segond1910) :
    ErreurBible invitant à l'import manuel.
    """

    version = VERSIONS_BIBLE.get(identifiant)

    if version is None:
        raise ErreurBible(
            f"Version de Bible inconnue : {identifiant}"
        )

    url = version.get("url_zip")

    if not url:
        raise ErreurBible(
            "Aucun lien de téléchargement direct "
            f"pour {version['nom']} : téléchargez le "
            "fichier OSIS depuis "
            f"{version['page_source']} puis utilisez "
            "« Charger depuis un fichier… »."
        )

    cible = chemin_version(identifiant, dossier)

    cible.parent.mkdir(parents=True, exist_ok=True)

    zip_provisoire = cible.with_suffix(".zip.part")
    osis_provisoire = cible.with_suffix(
        cible.suffix + ".part"
    )

    try:

        requete = urllib.request.Request(
            url,
            headers={"User-Agent": "TranscriptStudio"}
        )

        with urllib.request.urlopen(
            requete,
            timeout=60
        ) as reponse:

            total = reponse.headers.get(
                "Content-Length"
            )

            total = int(total) if total else None

            lus = 0

            with open(
                zip_provisoire,
                "wb"
            ) as fichier:

                while True:

                    if annulation is not None and (
                        annulation()
                    ):
                        raise ErreurBible(
                            "Téléchargement interrompu."
                        )

                    bloc = reponse.read(_TAILLE_BLOC)

                    if not bloc:
                        break

                    fichier.write(bloc)

                    lus += len(bloc)

                    if progression is not None:
                        progression(lus, total)

        #
        # Extraction du fichier OSIS du zip.
        #
        with zipfile.ZipFile(zip_provisoire) as archive:

            noms = [
                nom
                for nom in archive.namelist()
                if nom.lower().endswith(
                    (".osis.xml", ".xml")
                )
            ]

            if not noms:
                raise ErreurBible(
                    "L'archive téléchargée ne contient "
                    "aucun fichier OSIS."
                )

            with archive.open(noms[0]) as source:
                with open(
                    osis_provisoire,
                    "wb"
                ) as fichier:
                    shutil.copyfileobj(
                        source,
                        fichier
                    )

        ok, message = valider_fichier_bible(
            osis_provisoire
        )

        if not ok:
            raise ErreurBible(
                f"Fichier OSIS invalide — {message}"
            )

        osis_provisoire.replace(cible)

        zip_provisoire.unlink(missing_ok=True)

        return cible

    except ErreurBible:

        _nettoyer(zip_provisoire, osis_provisoire)
        raise

    except Exception as e:

        _nettoyer(zip_provisoire, osis_provisoire)

        raise ErreurBible(
            f"Téléchargement impossible : {e}"
        )


def _nettoyer(*fichiers) -> None:
    """
    Aucun fichier partiel conservé (règle 4).
    """

    for fichier in fichiers:

        try:
            Path(fichier).unlink(missing_ok=True)
        except OSError:
            pass
