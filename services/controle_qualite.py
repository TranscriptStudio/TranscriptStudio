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
