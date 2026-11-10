# services/lecteur_bible.py
"""
Lecteur de Bible intégré (P18.10 — décision David
du 2026-11-09 ; spec d'autorité BIBLE_JND_V2_2026-
11-09d §7, invariants 6-9) : page CONSULTATIVE PURE —
aucun LLM, aucun coût, aucune écriture hors les
réglages de l'app (dernier passage consulté).

- sélecteurs version → livre → chapitre → verset
  (facultatif, défaut v1) PILOTÉS PAR LES DONNÉES
  OSIS de la version sélectionnée (jamais de listes
  en dur) ;
- dernier passage consulté mémorisé dans les
  réglages de l'app et restauré à l'ouverture ;
  premier lancement : darbyR, livre 1, chapitre 1,
  v1 ; version proposée par défaut = dernière
  version consultée (aucun lien avec le contexte
  réunion/ouvrage) ;
- saisie directe de référence (ex. « Luc 1:5 »)
  réutilisant la normalisation P18.1 ; ambiguïté →
  suggestions de correspondances ; référence
  introuvable dans la version → écart signalé comme
  information, consultation possible dans les autres
  versions installées ;
- aucune version installée → renvoi vers le
  téléchargeur des réglages.
"""

from services.bibles import (
    VERSION_BIBLE_DEFAUT,
    VERSIONS_BIBLE,
    charger_bible_version,
    nom_court_bible,
    version_installee,
    versions_installees,
)
from services.jnd import extraire_references


class LecteurBibleError(Exception):
    """
    Erreur du lecteur de Bible (version non
    installée, passage hors limites...).
    """


PASSAGE_PREMIER_LANCEMENT = {
    "version": VERSION_BIBLE_DEFAUT,
    "livre": 1,
    "chapitre": 1,
    "verset": 1,
}


def versions_affichables(dossier=None) -> list:
    """
    Versions affichables dans le lecteur = versions
    INSTALLÉES (BIBLE_JND_V2 §7.6).
    """

    return versions_installees(dossier)


def charger_version(identifiant: str, dossier=None):
    """
    BibleJND d'une version installée — None si la
    version n'est pas installée.
    """

    return charger_bible_version(identifiant, dossier)


def structure_version(identifiant: str, dossier=None) -> list:
    """
    Structure OSIS de la version (livres, chapitres,
    nombre de versets) — dérivée du fichier OSIS,
    jamais en dur.
    """

    bible = charger_version(identifiant, dossier)

    if bible is None:
        return []

    return bible.structure()


def livre_par_index(structure: list, index: int):
    """
    Livre à l'index 1-based dans la structure OSIS
    (None si hors limites).
    """

    if not structure:
        return None

    index = max(1, min(int(index), len(structure)))

    return structure[index - 1]


def livre_par_osis(structure: list, osis_id: str):
    """
    Livre par identifiant OSIS (None si absent de
    cette versification).
    """

    for livre in structure:

        if livre["osis_id"] == osis_id:
            return livre

    return None


def resoudre_passage_initial(
    settings,
    dossier=None
) -> dict:
    """
    Passage restauré à l'ouverture du lecteur :
    le dernier passage consulté mémorisé dans les
    réglages de l'app, résolu contre la structure
    OSIS de sa version (si elle est installée) ;
    sinon la première version installée ; sinon le
    premier lancement (darbyR, livre 1, chapitre 1,
    v1).

    Retour : ``{"version", "livre" (index 1-based),
    "livre_osis", "chapitre", "verset", "bible",
    "structure"}``.
    """

    passage = (
        settings.get_dernier_passage_bible()
        if settings is not None
        else dict(PASSAGE_PREMIER_LANCEMENT)
    )

    installes = versions_affichables(dossier)

    version = passage.get("version")

    if version not in installes:

        version = (
            installes[0]
            if installes
            else VERSION_BIBLE_DEFAUT
        )

    structure = structure_version(version, dossier)

    bible = charger_version(version, dossier)

    # Le livre mémorisé prime par son identifiant
    # OSIS (robustesse aux versifications) ; sinon
    # l'index 1-based, borné à la structure.
    livre = livre_par_osis(
        structure,
        passage.get("livre_osis")
    )

    if livre is None:
        livre = livre_par_index(
            structure,
            passage.get("livre") or 1
        )

    if livre is None:

        return {
            "version": version,
            "livre": 1,
            "livre_osis": None,
            "chapitre": 1,
            "verset": 1,
            "bible": None,
            "structure": [],
        }

    chapitre = max(
        1,
        min(
            int(passage.get("chapitre") or 1),
            len(livre["chapitres"])
        )
    )

    nb_versets = (
        livre["chapitres"][chapitre - 1]["nb_versets"]
    )

    verset = max(
        1,
        min(int(passage.get("verset") or 1), nb_versets)
    )

    return {
        "version": version,
        "livre": structure.index(livre) + 1,
        "livre_osis": livre["osis_id"],
        "chapitre": chapitre,
        "verset": verset,
        "bible": bible,
        "structure": structure,
    }


def resoudre_saisie(
    texte: str,
    bible,
    autres_versions: dict = None
) -> dict:
    """
    Saisie directe d'une référence (ex. « Luc 1:5 »),
    normalisée par le parsing P18.1 :

    - aucune référence → ``{"statut": "aucune"}`` ;
    - une référence → ``{"statut": "ok", "reference",
      "existe", "existe_ailleurs"}`` ;
    - plusieurs → ``{"statut": "ambigu",
      "suggestions": [{"reference", "existe",
      "existe_ailleurs"}]}``.

    ``existe`` = la référence existe dans la version
    affichée ; ``existe_ailleurs`` = identifiants des
    autres versions installées où elle existe (écart
    de versification = information, BIBLE_JND_V2 §4).
    """

    references = extraire_references(texte or "")

    if not references:

        return {"statut": "aucune"}

    def _existe_ailleurs(reference):

        trouves = []

        for identifiant, autre in (
            (autres_versions or {}).items()
        ):

            if autre is not None and (
                autre.existe_reference(reference)
            ):
                trouves.append(identifiant)

        return trouves

    if len(references) == 1:

        reference = references[0]

        return {
            "statut": "ok",
            "reference": reference,
            "existe": (
                bible is not None
                and bible.existe_reference(reference)
            ),
            "existe_ailleurs": _existe_ailleurs(reference),
        }

    return {
        "statut": "ambigu",
        "suggestions": [
            {
                "reference": reference,
                "existe": (
                    bible is not None
                    and bible.existe_reference(reference)
                ),
                "existe_ailleurs": _existe_ailleurs(
                    reference
                ),
            }
            for reference in references
        ],
    }


def texte_chapitre(bible, osis_id: str, chapitre: int) -> dict:
    """
    Texte d'un chapitre : ``{"versets": [{"numero",
    "texte"}], "titre": "Livre C"}`` — dans l'ordre
    OSIS.
    """

    from services.jnd import nom_livre

    versets = (
        bible.versets
        .get(osis_id, {})
        .get(int(chapitre), {})
        if bible is not None
        else {}
    )

    return {
        "titre": f"{nom_livre(osis_id)} {chapitre}",
        "versets": [
            {"numero": numero, "texte": texte}
            for numero, texte in sorted(versets.items())
        ],
    }


def libelle_version(identifiant: str) -> str:
    """
    Libellé d'une version dans le sélecteur :
    « Darby révisée — Édition 2026 (rév. 2.3) ».
    """

    version = VERSIONS_BIBLE.get(identifiant)

    if version is None:
        return nom_court_bible(identifiant)

    return (
        nom_court_bible(identifiant)
        + " — "
        + version["edition"]
    )
