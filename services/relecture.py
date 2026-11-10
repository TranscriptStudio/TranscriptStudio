# services/relecture.py
"""
Aides à la relecture de l'ouvrage (P20.3 — aide à
l'écriture globale, emplacement UNIQUE page Ouvrage ;
amendement du 09/11) et présélection locale des
pensées redondantes (P20.6g).

Détection LOCALE, sans LLM (coût nul) :

- **récurrence d'emphase** : lexique paramétrable
  d'intensifs/adverbes (« puissamment »,
  « profondément »…) ; comptage par paragraphe,
  réunion et intervenant (via la provenance) ;
  signalement des densités anormales et des
  systématisations d'un bloc à l'autre ;
- **expressions récurrentes** : n-grammes de 2 à 6
  mots (normalisation : minuscules, ponctuation
  retirée, références bibliques masquées), comptage
  avec deux signaux — répartition (présence chez
  plusieurs réunions = tic du reformulateur ;
  concentrée dans une intervention = insistance
  légitime) et seuil d'occurrences ; regroupement
  des variantes par mots communs (familles) ;
- **présélection des pensées redondantes** (P20.6g)
  : comparaison normalisée des phrases courtes de
  la synthèse d'étude entre elles, SANS LLM — la
  confirmation LLM reste à la demande, sur la
  seule liste candidate.

Dans tous les cas : SIGNALEMENT UNIQUEMENT, jamais
de réécriture, jamais de remplacement suggéré. Les
occurrences sont rapportées avec les identifiants
des paragraphes de l'ouvrage (liens cliquables).
"""

import re

from models.ouvrage import TYPE_PARAGRAPHE


#
# Lexique paramétrable d'intensifs (P20.3) :
# surchargeable (ex. via les paramètres de l'étude,
# bloc controle_qualite.emphase.intensifs).
#

INTENSIFS_DEFAUT = [
    "puissamment",
    "profondément",
    "véritablement",
    "réellement",
    "particulièrement",
    "spécialement",
    "notamment",
    "essentiellement",
    "fondamentalement",
    "absolument",
    "totalement",
    "complètement",
    "pleinement",
    "largement",
    "sérieusement",
    "fortement",
    "hautement",
    "extrêmement",
    "incroyablement",
    "merveilleusement",
]

_MOTIF_REFERENCE = None


def _motif_reference():
    """
    Motif des références bibliques à MASQUER dans
    la normalisation : un nom de livre DU PARSING
    P18.1 (services.jnd) suivi d'un NUMÉRO de
    chapitre (sinon « est », « job »… du langage
    courant seraient masqués).
    """

    global _MOTIF_REFERENCE

    if _MOTIF_REFERENCE is None:

        from services.jnd import _MOTIF_LIVRES

        _MOTIF_REFERENCE = re.compile(
            r"(?<![\wÀ-ÿ])"
            rf"(?:{_MOTIF_LIVRES})"
            r"\s+\d{1,3}"
            r"(?:\s*[.:;,]\s*\d{1,3})?"
            r"(?:\s*[-–—]\s*\d{1,3})?",
            flags=re.IGNORECASE,
        )

    return _MOTIF_REFERENCE


def normaliser_pour_relecture(texte: str) -> str:
    """
    Normalisation pour la relecture : minuscules,
    RÉFÉRENCES BIBLIQUES MASQUÉES (avant retrait de
    la ponctuation, sinon « Luc 1:5 » laisserait
    « 5 »), ponctuation retirée, espaces resserrés.
    """

    if not texte:
        return ""

    nettoye = texte.lower().replace("’", "'")

    nettoye = _motif_reference().sub(" ", nettoye)

    nettoye = re.sub(
        r"[^\w\sÀ-ÿ']",
        " ",
        nettoye
    )

    return re.sub(r"\s+", " ", nettoye).strip()


def _mots(texte: str) -> list:
    normalise = normaliser_pour_relecture(texte)
    return normalise.split() if normalise else []


def _provenances(element):
    return list(getattr(element, "provenances", []) or [])


def _reunions_element(element) -> set:
    return {
        p.reunion
        for p in _provenances(element)
        if getattr(p, "reunion", "")
    }


def _locuteurs_element(element) -> set:
    return {
        p.locuteurs
        for p in _provenances(element)
        if getattr(p, "locuteurs", "")
    }


# ==================================================
# Récurrence d'emphase (P20.3, sans LLM).
# ==================================================


def emphase_ouvrage(
    document,
    lexique=None,
    seuil_paragraphe: int = 2,
    seuil_reunions: int = 3
) -> dict:
    """
    Comptage des intensifs du lexique (paramétrable)
    sur les paragraphes de l'ouvrage : par
    paragraphe, par réunion et par intervenant (via
    la provenance).

    Signalements (densités anormales et
    systématisations d'un bloc à l'autre) :
    - un même intensif présent ``seuil_paragraphe``
      fois AU MOINS dans un même paragraphe ;
    - un intensif présent dans au moins
      ``seuil_reunions`` réunions différentes
      (tic de reformulation, à l'utilisateur de
      trancher).

    Retour : ``{"par_paragraphe": [...], "totaux":
    {mot: {...}}, "signales": [...]}`` — occurrences
    avec identifiants de paragraphes (liens
    cliquables).
    """

    intensifs = [
        normaliser_pour_relecture(m)
        for m in (lexique or INTENSIFS_DEFAUT)
    ]

    intensifs = [m for m in intensifs if m]

    par_paragraphe = []
    totaux = {}

    for element in document.elements:

        if element.type != TYPE_PARAGRAPHE:
            continue

        mots = _mots(element.texte)

        compte = {}

        for mot in mots:

            if mot in intensifs:
                compte[mot] = compte.get(mot, 0) + 1

        if not compte:
            continue

        entree = {
            "id": element.id,
            "nb_mots": len(mots),
            "intensifs": compte,
            "reunions": sorted(_reunions_element(element)),
            "locuteurs": sorted(_locuteurs_element(element)),
        }

        par_paragraphe.append(entree)

        for mot, n in compte.items():

            total = totaux.setdefault(
                mot,
                {
                    "occurrences": 0,
                    "paragraphes": [],
                    "reunions": set(),
                    "locuteurs": set(),
                }
            )

            total["occurrences"] += n
            total["paragraphes"].append(element.id)
            total["reunions"].update(
                entree["reunions"]
            )
            total["locuteurs"].update(
                entree["locuteurs"]
            )

    signales = []

    for entree in par_paragraphe:

        if any(
            n >= seuil_paragraphe
            for n in entree["intensifs"].values()
        ):
            signales.append(entree["id"])

    for mot, total in totaux.items():

        if len(total["reunions"]) >= seuil_reunions:
            signales.extend(total["paragraphes"])

    for total in totaux.values():
        total["reunions"] = sorted(total["reunions"])
        total["locuteurs"] = sorted(total["locuteurs"])

    return {
        "lexique": intensifs,
        "par_paragraphe": par_paragraphe,
        "totaux": totaux,
        "signales": sorted(set(signales)),
    }


# ==================================================
# Expressions récurrentes (P20.3, sans LLM).
# ==================================================


def _n_grammes(mots: list, taille_min: int, taille_max: int):

    for taille in range(taille_min, taille_max + 1):

        if len(mots) < taille:
            continue

        for debut in range(
            0,
            len(mots) - taille + 1
        ):
            yield " ".join(mots[debut:debut + taille])


def expressions_recurrentes_ouvrage(
    document,
    taille_min: int = 2,
    taille_max: int = 6,
    occurrences_min: int = 3,
    reunions_min: int = 2,
    limite: int = 50
) -> list:
    """
    Expressions récurrentes de l'ouvrage (n-grammes
    de 2 à 6 mots, normalisation avec références
    masquées) : signalées quand elles apparaissent
    au moins ``occurrences_min`` fois dans au moins
    ``reunions_min`` réunions (tic du reformulateur ;
    une expression concentrée dans UNE réunion =
    insistance légitime, non signalée).

    Retour : liste triée ``{"expression",
    "occurrences", "paragraphes": [ids],
    "reunions", "locuteurs"}`` — occurrences
    cliquables (liens vers les paragraphes).
    """

    occurrences = {}
    paragraphes_par_expression = {}
    reunions_par_expression = {}
    locuteurs_par_expression = {}

    for element in document.elements:

        if element.type != TYPE_PARAGRAPHE:
            continue

        mots = _mots(element.texte)

        compte = {}

        for gram in _n_grammes(
            mots,
            taille_min,
            taille_max
        ):
            compte[gram] = compte.get(gram, 0) + 1

        for gram, total in compte.items():

            occurrences[gram] = (
                occurrences.get(gram, 0) + total
            )

            paragraphes_par_expression.setdefault(
                gram,
                set()
            ).add(element.id)

            reunions_par_expression.setdefault(
                gram,
                set()
            ).update(_reunions_element(element))

            locuteurs_par_expression.setdefault(
                gram,
                set()
            ).update(_locuteurs_element(element))

    candidates = []

    for expression, total in occurrences.items():

        reunions = reunions_par_expression[expression]

        if (
            total >= occurrences_min
            and len(reunions) >= reunions_min
        ):
            candidates.append({
                "expression": expression,
                "occurrences": total,
                "paragraphes": sorted(
                    paragraphes_par_expression[expression]
                ),
                "reunions": sorted(reunions),
                "locuteurs": sorted(
                    locuteurs_par_expression[expression]
                ),
            })

    candidates.sort(
        key=lambda item: (
            -item["occurrences"],
            item["expression"]
        )
    )

    return candidates[:limite]


_MOTS_VIDES = {
    "le", "la", "les", "un", "une", "des", "de", "du",
    "et", "ou", "mais", "donc", "or", "ni", "car",
    "que", "qui", "quoi", "dont", "où",
    "ce", "cet", "cette", "ces", "se", "sa", "son",
    "ses", "leur", "leurs", "il", "elle", "ils",
    "elles", "nous", "vous", "on", "je", "tu",
    "est", "sont", "était", "être", "avoir", "a",
    "au", "aux", "en", "dans", "sur", "sous", "par",
    "pour", "avec", "sans", "chez", "vers",
    "plus", "moins", "très", "tant", "aussi",
    "ne", "pas", "point", "rien", "jamais", "toujours",
    "y", "en",
}


def familles_expressions(candidates: list) -> list:
    """
    Regroupe les variantes d'expressions par MOTS
    COMMUNS de contenu (hors mots vides) : « ce qui
    s'offre à nos cœurs / à la foi » forme une
    famille. Le regroupement reste LOCAL (la passe
    LLM optionnelle, à la demande, porte sur la
    seule liste des familles candidates).
    """

    familles = []
    assignes = set()

    for i, candidat in enumerate(candidates):

        if i in assignes:
            continue

        mots_i = {
            m for m in candidat["expression"].split()
            if m not in _MOTS_VIDES
        }

        groupe = [candidat]
        assignes.add(i)

        for j in range(i + 1, len(candidates)):

            if j in assignes:
                continue

            mots_j = {
                m for m in candidates[j]["expression"].split()
                if m not in _MOTS_VIDES
            }

            communs = mots_i & mots_j

            if communs:
                groupe.append(candidates[j])
                assignes.add(j)
                mots_i = mots_i | mots_j

        if len(groupe) > 1:

            familles.append({
                "expressions": [
                    c["expression"] for c in groupe
                ],
                "occurrences": sum(
                    c["occurrences"] for c in groupe
                ),
                "paragraphes": sorted({
                    p
                    for c in groupe
                    for p in c["paragraphes"]
                }),
                "reunions": sorted({
                    r
                    for c in groupe
                    for r in c["reunions"]
                }),
            })

        else:

            familles.append({
                "expressions": [candidat["expression"]],
                "occurrences": candidat["occurrences"],
                "paragraphes": candidat["paragraphes"],
                "reunions": candidat["reunions"],
            })

    familles.sort(
        key=lambda f: (
            -f["occurrences"],
            f["expressions"][0]
        )
    )

    return familles


# ==================================================
# Présélection des pensées redondantes (P20.6g,
# locale, sans LLM).
# ==================================================


_MOTIF_PREFIXE = re.compile(
    r"^\s*(?:R\d+|réunion\s+\S+)\s*[—–-]\s*[^:]{0,40}:\s*",
    re.IGNORECASE,
)


def _phrases(texte: str) -> list:
    """
    Découpe un texte en phrases courtes (la
    synthèse d'étude est au format « phrases
    courtes par pensée ») — le préfixe
    « R1 — Philippe : » (locuteur) est retiré pour
    la comparaison.
    """

    phrases = re.split(r"(?<=[.!?…])\s+", texte or "")

    nettoyees = []

    for p in phrases:

        p = _MOTIF_PREFIXE.sub("", p.strip())

        if p and len(p.split()) >= 3:
            nettoyees.append(p)

    return nettoyees


def _similarite(mots_a: list, mots_b: list) -> float:
    """
    Recouvrement de Jaccard entre deux ensembles
    de mots (présélection locale normalisée).
    """

    a, b = set(mots_a), set(mots_b)

    if not a or not b:
        return 0.0

    return len(a & b) / len(a | b)


SEUIL_SIMILARITE = 0.6


def preselectionner_pensees_redondantes(
    texte_synthese: str,
    seuil: float = SEUIL_SIMILARITE
) -> list:
    """
    P20.6g : présélection LOCALE (sans LLM) des
    pensées redondantes dans la synthèse d'étude :
    comparaison normalisée des phrases courtes
    entre elles (recouvrement de mots >= seuil).

    Retour : liste de groupes ``{"phrases": [...],
    "normalisees": [...]}`` (au moins 2 phrases).
    """

    phrases = _phrases(texte_synthese)

    normalisees = [
        normaliser_pour_relecture(p) for p in phrases
    ]

    mots = [n.split() for n in normalisees]

    groupes = []
    vus = set()

    for i in range(len(phrases)):

        if i in vus:
            continue

        groupe = [i]
        vus.add(i)

        for j in range(i + 1, len(phrases)):

            if j in vus:
                continue

            if _similarite(mots[i], mots[j]) >= seuil:
                groupe.append(j)
                vus.add(j)

        if len(groupe) >= 2:

            groupes.append({
                "phrases": [phrases[k] for k in groupe],
                "normalisees": [
                    normalisees[k] for k in groupe
                ],
            })

    return groupes


def lier_pensees_aux_paragraphes(
    document,
    groupes: list
) -> list:
    """
    P20.6g : relie chaque groupe de pensées
    redondantes aux PARAGRAPHES de l'ouvrage dont
    le texte normalisé contient (ou recouvre à
    >= 80 %) la pensée — liens cliquables via la
    provenance P19.1. Signalement uniquement.
    """

    paragraphes = [
        e for e in document.elements
        if e.type == TYPE_PARAGRAPHE
    ]

    textes_norm = {
        p.id: normaliser_pour_relecture(p.texte)
        for p in paragraphes
    }

    mots_paragraphes = {
        p.id: set(textes_norm[p.id].split())
        for p in paragraphes
    }

    resultat = []

    for groupe in groupes:

        ids = []

        for normalisee in groupe["normalisees"]:

            mots_pensee = set(normalisee.split())

            if not mots_pensee:
                continue

            for p in paragraphes:

                mots_p = mots_paragraphes[p.id]

                if not mots_p:
                    continue

                recouvrement = len(
                    mots_pensee & mots_p
                ) / len(mots_pensee)

                if (
                    normalisee in textes_norm[p.id]
                    or recouvrement >= 0.8
                ):
                    if p.id not in ids:
                        ids.append(p.id)

        resultat.append({
            "phrases": groupe["phrases"],
            "paragraphes": ids,
        })

    return resultat
