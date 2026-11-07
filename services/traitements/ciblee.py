"""
Sémantique de la relance ciblée sur sélection
(CORRECTIFS_RELANCE_CIBLEE_V2_2026-11-07a.md —
fait autorité pour ses points).

**Règle générale** : la relance ciblée retravaille
UNIQUEMENT le passage sélectionné, et c'est
l'APPLICATION qui raccorde, pas le LLM.

- Inv. S1 : le message LLM contient le TEXTE du
  passage sélectionné (pas des offsets — un LLM ne
  compte pas les caractères) ; le LLM doit retourner
  UNIQUEMENT le passage retravaillé.
- Inv. S2 : l'application remplace
  programmatiquement la tranche [debut, fin] du
  texte courant par la réponse (strippée) — le reste
  est conservé octet pour octet, garanti par
  construction.
- Inv. S3 : la consigne est énoncée EN DERNIER,
  explicitement prioritaire (y compris sur la
  langue).
- Inv. S4 : le contexte envoyé est minimal, en
  lecture seule (texte courant complet marqué « ne
  pas reproduire ») — JAMAIS la source ni les
  versions antérieures (coût divisé, et c'est ce
  qui causait la régénération de bout en bout).
- Garde-fous : réponse vide → erreur propre, rien
  n'est consigné ; réponse > 3× le passage →
  acceptée mais la version est marquée.
"""


class RelanceVideError(Exception):
    """
    Garde-fou : le modèle n'a rien produit — erreur
    propre, RIEN n'est consigné.
    """

    pass


# Réponse acceptée mais marquée au-delà de ce
# rapport (le retour arrière reste le filet).
RAPPORT_LONGUEUR_MAX = 3

AVERTISSEMENT_LONGUE = (
    "reponse_plus_longue_que_le_passage"
)


def extraire_passage(texte: str, selection: dict) -> str:
    """
    Le texte du passage sélectionné (Inv. S1 : envoyé
    au LLM, pas les offsets seuls).
    """

    debut = int(selection.get("debut", 0))
    fin = int(selection.get("fin", 0))

    if fin < debut:
        debut, fin = fin, debut

    return (texte or "")[debut:fin]


def raccorder(
    texte: str,
    selection: dict,
    reponse: str
) -> str:
    """
    Inv. S2 : remplacement programmatique de la
    tranche [debut, fin] par la réponse strippée — le
    reste du texte est conservé octet pour octet.
    """

    debut = int(selection.get("debut", 0))
    fin = int(selection.get("fin", 0))

    if fin < debut:
        debut, fin = fin, debut

    return (
        (texte or "")[:debut]
        + (reponse or "").strip()
        + (texte or "")[fin:]
    )


def verifier_reponse(
    reponse: str,
    passage: str
) -> tuple:
    """
    Garde-fous sur la réponse du modèle.

    Retour : ``(reponse_strippee, avertissement)``.
    Lève ``RelanceVideError`` si la réponse est vide
    (rien n'est consigné par l'appelant).
    """

    reponse = (reponse or "").strip()

    if not reponse:
        raise RelanceVideError(
            "Le modèle n'a rien produit : rien n'est "
            "consigné."
        )

    avertissement = None

    if len(passage) > 0 and (
        len(reponse) > RAPPORT_LONGUEUR_MAX * len(passage)
    ):
        avertissement = AVERTISSEMENT_LONGUE

    return reponse, avertissement


def message_ciblee(
    passage: str,
    consigne: str = None,
    contexte: str = None
) -> str:
    """
    Message de la relance ciblée (Inv. S1/S3/S4) :
    passage en clair, contexte courant en lecture
    seule, consigne EN DERNIER et prioritaire.
    """

    parties = [
        "Passage à retravailler :\n"
        + (passage or "").strip()
    ]

    if contexte:
        parties.append(
            "Texte courant complet (pour contexte "
            "seulement — ne pas reproduire, ne pas "
            "retravailler) :\n"
            + contexte.strip()
        )

    consigne_txt = (
        consigne.strip()
        if consigne and consigne.strip()
        else "Retravailler ce passage."
    )

    parties.append(
        "Consigne (PRIORITAIRE, y compris sur la "
        "langue) : "
        + consigne_txt
        + "\n"
        "Répondre UNIQUEMENT par le passage "
        "retravaillé — aucun préambule, aucun "
        "commentaire, aucun texte hors passage."
    )

    return "\n\n".join(parties)
