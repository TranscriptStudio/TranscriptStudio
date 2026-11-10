# services/prompts.py
"""
Bibliothèque de prompts (P16-ter, spec
UI_GESTION_PROMPTS_V2_2026-10-31a.md).

La bibliothèque vit dans le dossier de paramétrage
de l'app : ``<données app>/prompts/<usage>.md``.

Un usage sans fichier vaut le DÉFAUT EMBARQUÉ
(resources/prompts/) — invariant 2 : la lecture
ne crée jamais de fichier, et les défauts
embarqués ne sont jamais modifiés (invariant 1).

La bibliothèque ne touche jamais une étude
existante (invariant 3) : elle n'initialise que
les NOUVELLES études (services.etude_io.
parametres_par_defaut) ; le copie locale d'une
étude n'évolue que par édition explicite ou
« Recharger depuis la bibliothèque ».
"""

import hashlib
from pathlib import Path

from services.app_paths import APP_DATA_DIR
from services.resources import resource_path


USAGE_REFORMULATION = "reformulation"
USAGE_RESUME = "resume"
USAGE_FUSION = "fusion"
# P20.6a : prompt dédié de la synthèse d'étude —
# prompts/synthese_etude.md dans la bibliothèque.
USAGE_SYNTHESE_ETUDE = "synthese_etude"

LIBELLES_USAGES = {
    USAGE_REFORMULATION: "Reformulation",
    USAGE_RESUME: "Résumé",
    # P19.4-bis (ARBITRAGE_PROMPT_FUSION) : usage
    # « Fusion de pensées » — entrée « Fusion » du
    # sélecteur de ⚙ Prompts.
    USAGE_FUSION: "Fusion de pensées",
    # P20.6a : entrée « Synthèse d'étude ».
    USAGE_SYNTHESE_ETUDE: "Synthèse d'étude",
}

FICHIERS_DEFAUT_EMBARQUES = {
    USAGE_REFORMULATION: (
        "prompt_reformulation_v2.md"
    ),
    USAGE_RESUME: (
        "prompt_resume_v2.md"
    ),
    USAGE_FUSION: (
        "prompt_fusion_v2.md"
    ),
    USAGE_SYNTHESE_ETUDE: (
        "prompt_synthese_etude.md"
    ),
}

DOSSIER_BIBLIOTHEQUE = "prompts"

EXTENSIONS_IMPORT_EXPORT = (".md", ".txt")


class PromptsError(Exception):
    """
    Erreur de la bibliothèque de prompts (usage
    inconnu, fichier illisible...).
    """

    pass


def dossier_bibliotheque() -> Path:
    """
    Dossier de la bibliothèque dans le dossier de
    paramétrage de l'app.
    """

    return APP_DATA_DIR / DOSSIER_BIBLIOTHEQUE


def _valider_usage(usage: str) -> str:

    if usage not in FICHIERS_DEFAUT_EMBARQUES:
        raise PromptsError(
            f"Usage de prompt inconnu : {usage} "
            f"(attendus : "
            f"{', '.join(FICHIERS_DEFAUT_EMBARQUES)})"
        )

    return usage


def chemin_bibliotheque(
    usage: str,
    dossier=None
) -> Path:
    """
    Chemin du fichier de bibliothèque d'un usage :
    ``prompts/<usage>.md`` (le fichier peut être
    absent — il vaut alors le défaut embarqué).
    """

    _valider_usage(usage)

    base = (
        Path(dossier)
        if dossier is not None
        else dossier_bibliotheque()
    )

    return base / f"{usage}.md"


def normaliser_texte_prompt(texte: str) -> str:
    """
    Normalise un texte de prompt pour stockage et
    comparaison : retours de ligne simples, pas
    de blancs aux extrémités (même convention que
    la lecture des défauts embarqués).
    """

    if texte is None:
        return ""

    texte = texte.replace("\r\n", "\n")
    texte = texte.replace("\r", "\n")

    return texte.strip()


def lire_defaut_embarque(usage: str) -> str:
    """
    Prompt de RÉFÉRENCE embarqué (resources/),
    valeur de repli de la bibliothèque — jamais
    modifié par l'app (invariant 1).
    """

    _valider_usage(usage)

    chemin = resource_path(
        "resources/prompts/"
        f"{FICHIERS_DEFAUT_EMBARQUES[usage]}"
    )

    with open(
        chemin,
        "r",
        encoding="utf-8"
    ) as fichier:
        return fichier.read().strip()


def lire_bibliotheque(
    usage: str,
    dossier=None
) -> tuple:
    """
    Lit la valeur COURANTE de la bibliothèque d'un
    usage : fichier ``prompts/<usage>.md`` s'il
    existe, défaut embarqué sinon.

    Retour : ``(texte, personnalise)`` —
    ``personnalise`` vaut True si un fichier de
    bibliothèque existe.

    La lecture ne crée JAMAIS de fichier
    (invariant 2).
    """

    _valider_usage(usage)

    chemin = chemin_bibliotheque(usage, dossier)

    if not chemin.exists():
        return (
            lire_defaut_embarque(usage),
            False,
        )

    try:

        with open(
            chemin,
            "r",
            encoding="utf-8"
        ) as fichier:
            texte = fichier.read()

    except OSError as e:
        raise PromptsError(
            f"Bibliothèque de prompts illisible "
            f"({chemin}) : {e}"
        )

    return (
        normaliser_texte_prompt(texte),
        True,
    )


def ecrire_bibliotheque(
    usage: str,
    texte: str,
    dossier=None
) -> Path:
    """
    Écrit le prompt d'un usage dans la
    bibliothèque (crée le dossier si besoin) et
    retourne le chemin écrit.

    Seuls les tests, « Enregistrer » et
    « Promulguer » appellent cette fonction :
    jamais une lecture (invariant 2).
    """

    _valider_usage(usage)

    chemin = chemin_bibliotheque(usage, dossier)

    chemin.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        chemin,
        "w",
        encoding="utf-8",
        newline="\n"
    ) as fichier:
        fichier.write(
            normaliser_texte_prompt(texte)
        )

    return chemin


def reinitialiser_bibliotheque(
    usage: str,
    dossier=None
) -> bool:
    """
    Réinitialise un usage aux DÉFAUTS EMBARQUÉS :
    supprime le fichier de bibliothèque (rien
    d'autre : invariant 1).

    Retour : True si un fichier existait et a été
    supprimé.
    """

    _valider_usage(usage)

    chemin = chemin_bibliotheque(usage, dossier)

    if not chemin.exists():
        return False

    chemin.unlink()

    return True


def prompt_initial(
    usage: str,
    dossier=None
) -> str:
    """
    Valeur d'initialisation du prompt d'une
    NOUVELLE étude : la bibliothèque (fichier
    s'il existe, défaut embarqué sinon).
    """

    return lire_bibliotheque(usage, dossier)[0]


def hash_prompt(texte: str) -> str:
    """
    Hash COURT d'un texte de prompt : 8 premiers
    caractères hexadécimaux du SHA-256 (indicateur
    de divergence et traçabilité des versions,
    P16-ter §5).
    """

    normalise = normaliser_texte_prompt(texte)

    if not normalise:
        return ""

    return hashlib.sha256(
        normalise.encode("utf-8")
    ).hexdigest()[:8]
