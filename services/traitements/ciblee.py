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
  version marquée ; réponse contenant un fragment
  du texte original (≥ 6 mots consécutifs, série 2
  Inv. S7) → version consignée mais avertissement
  affiché — JAMAIS de blocage, JAMAIS de
  modification automatique de la réponse.

Série 2 (CORRECTIFS_RELANCE_CIBLEE_V2_2026-11-07b) :
- Inv. S6 : instruction anti-reproduction explicite,
  en dernier dans le message ;
- Inv. S7 : garde anti-résidu (≥ 6 mots consécutifs
  du passage original retrouvés dans la réponse,
  comparaison normalisée) ;
- Inv. S8 : le passage envoyé est le texte EXACT de
  la tranche [debut, fin] telle qu'elle sera
  remplacée.
"""

import re


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

# Série 2 (Inv. S7) : fragment du texte original
# retrouvé dans la réponse (≥ 6 mots consécutifs).
AVERTISSEMENT_RESIDU = (
    "fragment_du_texte_original"
)

# Seuil de détection du résidu (mots consécutifs).
SEUIL_MOTS_RESIDU = 6


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

    Retour : ``(reponse_strippee, avertissements)``
    (liste de marqueurs : longueur, résidu).
    Lève ``RelanceVideError`` si la réponse est vide
    (rien n'est consigné par l'appelant).
    """

    reponse = (reponse or "").strip()

    if not reponse:
        raise RelanceVideError(
            "Le modèle n'a rien produit : rien n'est "
            "consigné."
        )

    avertissements = []

    if len(passage) > 0 and (
        len(reponse) > RAPPORT_LONGUEUR_MAX * len(passage)
    ):
        avertissements.append(AVERTISSEMENT_LONGUE)

    # Inv. S7 : garde anti-résidu.
    if detecter_residu(reponse, passage):
        avertissements.append(AVERTISSEMENT_RESIDU)

    return reponse, avertissements


def _normaliser(texte: str) -> str:
    """
    Normalisation pour la comparaison anti-résidu
    (Inv. S7) : minuscules, ponctuation retirée,
    espaces et retours à la ligne ramenés à un
    espace.
    """

    texte = (texte or "").lower()
    texte = re.sub(
        r"[^\w\s]",
        " ",
        texte,
        flags=re.UNICODE
    )

    return " ".join(texte.split())


def detecter_residu(
    reponse: str,
    passage: str,
    seuil: int = SEUIL_MOTS_RESIDU
) -> bool:
    """
    Inv. S7 : la réponse contient-elle une sous-chaîne
    de ``seuil`` mots consécutifs (6 par défaut)
    présente dans le passage original ? Comparaison
    normalisée (minuscules, ponctuation ignorée,
    espaces ramenés à un).

    Jamais de blocage : simple signalement.
    """

    mots_reponse = _normaliser(reponse).split()
    mots_passage = _normaliser(passage).split()

    if (
        len(mots_passage) < seuil
        or len(mots_reponse) < seuil
    ):
        return False

    fenetres_passage = {
        " ".join(mots_passage[i:i + seuil])
        for i in range(
            len(mots_passage) - seuil + 1
        )
    }

    return any(
        " ".join(mots_reponse[i:i + seuil])
        in fenetres_passage
        for i in range(
            len(mots_reponse) - seuil + 1
        )
    )


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
        #
        # Inv. S6 (série 2) : instruction
        # anti-reproduction explicite, EN DERNIER.
        #
        "Répondre UNIQUEMENT par le passage "
        "retravaillé, complet (du premier au "
        "dernier mot du passage), sans préambule, "
        "sans commentaire, et sans reproduire "
        "aucun fragment du texte original."
    )

    return "\n\n".join(parties)
