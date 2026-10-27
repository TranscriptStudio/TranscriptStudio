# services/controle_qualite.py
"""
Contrôle qualité local (P16.4).

Feuille de route §5 — sans LLM, affiché comme
indicateurs/suggestions, **jamais de modification
automatique du texte** :

- §5.1 **rapport de longueur** : mots résultat vs
  mots source ; avertissement si le résultat dépasse
  ~120 % de la source ;
- §5.3 **interdits stylistiques** : recherche locale
  de motifs dans une liste éditable (« l'orateur »,
  « le frère », « nous avons vu que », « il convient
  de »...), stockée dans les paramètres de l'étude
  (contrat §10, controle_qualite).

Les références bibliques (§5.2) et les citations
JND (§5.4) arrivent en P18 ; la récurrence d'emphase
(P20) portera sur l'ouvrage, pas sur le bloc.
"""

import re

#
# Seuil du rapport de longueur (feuille de route
# §5.1 : avertissement si > ~120 %).
#

SEUIL_LONGUEUR_POURCENT = 120

#
# Interdits stylistiques par défaut (§5.3, liste
# éditable dans les paramètres de l'étude).
#

INTERDITS_STYLISTIQUES_DEFAUT = [
    "l'orateur",
    "le frère",
    "la sœur",
    "nous avons vu que",
    "il convient de",
    "il faut remarquer que",
]


def compter_mots(texte: str) -> int:
    """
    Nombre de mots d'un texte (séquences de
    caractères non-espaces).
    """

    if not texte:
        return 0

    return len(
        re.findall(r"\S+", texte)
    )


def rapport_longueur(
    source: str,
    resultat: str,
    seuil_pourcent: int = SEUIL_LONGUEUR_POURCENT
) -> dict:
    """
    §5.1 : rapport de longueur entre le texte source
    et le résultat ; avertissement si le résultat
    dépasse le seuil (en pourcentage de la source).

    Retourne :
    - ``mots_source``, ``mots_resultat`` ;
    - ``ratio_pourcent`` (None si source vide) ;
    - ``avertissement`` (bool) ;
    - ``message`` (libellé court pour l'UI).
    """

    mots_source = compter_mots(source)
    mots_resultat = compter_mots(resultat)

    ratio = None
    avertissement = False
    message = "Longueur : —"

    if mots_source > 0:

        ratio = round(
            100.0 * mots_resultat / mots_source
        )

        avertissement = (
            ratio > seuil_pourcent
        )

        if avertissement:
            message = (
                f"Longueur : {mots_resultat} mots "
                f"pour {mots_source} "
                f"(+{ratio - 100} %) — la reformulation "
                "est nettement plus longue que la source."
            )
        else:
            message = (
                f"Longueur : {mots_resultat} mots "
                f"pour {mots_source} ({ratio} %)."
            )

    return {
        "mots_source": mots_source,
        "mots_resultat": mots_resultat,
        "ratio_pourcent": ratio,
        "avertissement": avertissement,
        "message": message,
    }


def interdits_stylistiques(
    texte: str,
    motifs: list
) -> list:
    """
    §5.3 : recherche locale (insensible à la casse)
    des motifs interdits dans le texte.

    Retourne une liste triée par nombre
    d'occurrences décroissant :
    ``{"motif", "occurrences", "positions"}``
    (positions = index de début des occurrences).
    """

    trouves = []

    if not texte or not motifs:
        return trouves

    for motif in motifs:

        if not motif or not motif.strip():
            continue

        positions = [
            occurrence.start()
            for occurrence in re.finditer(
                re.escape(motif),
                texte,
                flags=re.IGNORECASE
            )
        ]

        if positions:
            trouves.append({
                "motif": motif,
                "occurrences": len(positions),
                "positions": positions,
            })

    trouves.sort(
        key=lambda item: item["occurrences"],
        reverse=True
    )

    return trouves


def controles_bloc(
    source: str,
    resultat: str,
    controle_qualite: dict = None
) -> dict:
    """
    Contrôles qualité locaux d'un bloc (indicateurs
    discrets de la page Reformulation, spec UI §4) :
    longueur + interdits stylistiques (les références
    et citations arrivent en P18).

    ``controle_qualite`` : la section
    ``controle_qualite`` des paramètres de l'étude
    (contrat §10) — liste éditable
    ``interdits_stylistiques``.
    """

    controle_qualite = controle_qualite or {}

    motifs = controle_qualite.get(
        "interdits_stylistiques",
        INTERDITS_STYLISTIQUES_DEFAUT
    )

    longueur = rapport_longueur(source, resultat)

    interdits = interdits_stylistiques(
        resultat,
        motifs
    )

    if interdits:

        resume = ", ".join(
            f"« {trouve['motif']} » "
            f"(×{trouve['occurrences']})"
            for trouve in interdits
        )

        message_interdits = (
            "Interdits stylistiques : " + resume
        )

    else:

        message_interdits = (
            "Interdits stylistiques : aucun."
        )

    return {
        "longueur": longueur,
        "interdits": interdits,
        "message_interdits": message_interdits,
        "nb_alertes": (
            (1 if longueur["avertissement"] else 0)
            + len(interdits)
        ),
    }


#
# P17.3 — expressions récurrentes entre réunions
# (contrôle qualité étendu : comparaison des
# formules les plus fréquentes de l'étude, à titre
# indicatif — signalement seulement, jamais de
# suggestion de remplacement, jamais de réécriture).
#

RECURRENTES_TAILLE_MIN = 3
RECURRENTES_TAILLE_MAX = 6
RECURRENTES_OCCURRENCES_MIN = 3
RECURRENTES_REUNIONS_MIN = 2
RECURRENTES_LIMITE = 30


def _normaliser_expression(texte: str) -> str:
    """
    Normalisation pour la comparaison : minuscules,
    ponctuation retirée, espaces resserrées.
    """

    if not texte:
        return ""

    nettoye = re.sub(
        r"[^\w\sÀ-ÿ']",
        " ",
        texte.lower()
    )

    return re.sub(r"\s+", " ", nettoye).strip()


def _n_grammes(texte: str, taille_min: int, taille_max: int):
    """
    Itère les n-grammes de ``taille_min`` à
    ``taille_max`` mots du texte normalisé.
    """

    mots = _normaliser_expression(texte).split(" ")

    for taille in range(taille_min, taille_max + 1):

        if len(mots) < taille:
            continue

        for debut in range(0, len(mots) - taille + 1):
            yield " ".join(mots[debut:debut + taille])


def _textes_valides_etude(etude_ouverte):
    """
    Textes validés par réunion (reformulations
    validées + résumé validé), dans l'ordre des
    réunions de l'étude.

    Retour : liste (réunion, liste de textes).
    """

    from services.decoupage import blocs_actifs

    par_reunion = []

    for reunion in etude_ouverte.etude.ordre_reunions:

        textes = []

        for bloc in blocs_actifs(etude_ouverte, reunion):

            resultat = etude_ouverte.reformulations.get(
                bloc.fid
            )

            if not resultat or not resultat.versions:
                continue

            for version in reversed(resultat.versions):

                if (
                    version.validation
                    and version.validation.statut
                    == "valide"
                ):
                    textes.append(version.texte)
                    break

        resume = etude_ouverte.resumes.get(reunion)

        if resume:

            for version in reversed(resume.versions):

                if (
                    version.validation
                    and version.validation.statut
                    == "valide"
                ):
                    textes.append(version.texte)
                    break

        if textes:
            par_reunion.append((reunion, textes))

    return par_reunion


def expressions_recurrentes(
    etude_ouverte,
    taille_min: int = RECURRENTES_TAILLE_MIN,
    taille_max: int = RECURRENTES_TAILLE_MAX,
    occurrences_min: int = RECURRENTES_OCCURRENCES_MIN,
    reunions_min: int = RECURRENTES_REUNIONS_MIN,
    limite: int = RECURRENTES_LIMITE
) -> list:
    """
    P17.3 : formules les plus fréquentes de l'étude,
    comparées entre réunions — gratuit, sans LLM,
    signalement indicatif seulement.

    Une expression est signalée quand elle apparaît
    au moins ``occurrences_min`` fois dans au moins
    ``reunions_min`` réunions (le vocabulaire du
    thème de l'étude ressort inévitablement : le
    filtre sur les réunions concentre le rapport sur
    les tics de reformulation).

    Retour : liste triée
    ``{"expression", "occurrences", "reunions"}``,
    limitée à ``limite`` entrées.
    """

    occurrences = {}
    reunions_par_expression = {}

    for reunion, textes in _textes_valides_etude(
        etude_ouverte
    ):

        compte_reunion = {}

        for texte in textes:

            for gram in _n_grammes(
                texte,
                taille_min,
                taille_max
            ):

                compte_reunion[gram] = (
                    compte_reunion.get(gram, 0) + 1
                )

        for gram, total in compte_reunion.items():

            occurrences[gram] = (
                occurrences.get(gram, 0) + total
            )

            reunions_par_expression.setdefault(
                gram,
                set()
            ).add(reunion)

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
                "reunions": sorted(reunions),
            })

    candidates.sort(
        key=lambda item: (
            -item["occurrences"],
            item["expression"]
        )
    )

    return candidates[:limite]
