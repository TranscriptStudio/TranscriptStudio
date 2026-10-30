# services/rattachement.py
"""
Rattachement des réunions aux études (P18.6,
ARBITRAGE_EXCLUSIVITE_REUNIONS_2026-10-29 —
inversion de l'invariant 13.5 du contrat).

Règles :

- une réunion (projet v1) appartient à **0 ou 1**
  étude à tout instant (invariant §9.1) ;
- le rattachement est possible à tout moment, dès
  le prétraitement ;
- un rattachement vers une réunion déjà rattachée
  est un **changement d'étude** : confirmation
  demandée, puis option A — les traitements déjà
  réalisés (découpage, reformulations, résumés,
  validations) **restent à l'ancienne étude**,
  aucun déplacement ni copie ; la réunion change
  seulement de rattachement (invariant §9.5) ;
- aucun changement de format : l'étude référence
  toujours la réunion, l'unicité est contrôlée à
  l'écriture (aux moments de rattachement).

Les études « connues » de l'app sont les études
récentes des réglages (aucun registre global de
studies n'existe ; les dossiers à explorer sont
fournis par l'appelant, ce qui rend ces fonctions
pures et testables).
"""

from pathlib import Path

from services.etude_io import (
    DOSSIER_REUNIONS,
    EtudeError,
    EtudeOuverte,
    ajouter_reunion,
    ouvrir_etude,
    sauvegarder_etude,
)

import json


class RattachementError(Exception):
    """
    Erreur de rattachement (exclusivité violée,
    étude illisible, projet v1 inconnu).
    """


def lire_etude_legere(dossier_etude):
    """
    Métadonnées légères d'une étude (P18.6-bis
    série 4, menu déroulant du hub) : ``titre``,
    ``theme`` et ``modification`` lus directement
    d'etude.json — SANS charger le registre FID,
    les traitements ni les réunions.

    Retourne None si le dossier n'est pas une
    étude lisible.
    """

    fichier = Path(dossier_etude) / "etude.json"

    if not fichier.is_file():
        return None

    try:

        with open(
            fichier,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

    except (OSError, ValueError):
        return None

    return {
        "titre": data.get("titre", ""),
        "theme": data.get("theme", ""),
        "modification": data.get(
            "modification", ""
        ),
    }


def reunions_des_etudes(dossier_etude) -> dict:
    """
    Lecture légère d'une étude : {nom de réunion
    -> chemin du projet v1 résolu}. Ne charge NI
    le registre FID, NI les traitements — le
    rattachement n'en a pas besoin.

    Retourne {} si le dossier n'est pas une étude
    lisible.
    """

    dossier = Path(dossier_etude)

    fichier = dossier / "etude.json"

    if not fichier.is_file():
        return {}

    try:

        with open(
            fichier,
            "r",
            encoding="utf-8"
        ) as f:
            _ = json.load(f)

    except (OSError, ValueError):
        return {}

    resultat = {}

    dossier_reunions = dossier / DOSSIER_REUNIONS

    if not dossier_reunions.is_dir():
        return {}

    for chemin_json in (
        dossier_reunions.glob("*.json")
    ):

        try:

            with open(
                chemin_json,
                "r",
                encoding="utf-8"
            ) as f:
                data = json.load(f)

        except (OSError, ValueError):
            continue

        chemin_projet = data.get(
            "chemin_projet"
        )

        chemin_absolu = data.get(
            "chemin_absolu"
        )

        resolu = None

        if chemin_projet:

            candidat = (
                dossier / chemin_projet
            )

            if candidat.exists():
                resolu = candidat.resolve()

        if (
            resolu is None
            and chemin_absolu
            and Path(chemin_absolu).exists()
        ):
            resolu = (
                Path(chemin_absolu).resolve()
            )

        resultat[chemin_json.stem] = (
            resolu if resolu else chemin_absolu
        )

    return resultat


def rattachement_de(
    chemin_projet,
    dossiers_etudes
):
    """
    L'étude (parmi les dossiers fournis) qui
    référence la réunion, avec le nom de la
    réunion dedans.

    Retour : (dossier_etude, nom) ou None si la
    réunion est autonome (aucune étude).

    Invariant §9.1 : la première étude trouvée
    est retournée ; l'exclusivité garantit qu'il
    n'y en a pas d'autre (les études existantes
    non conformes, s'il y en a, ne sont pas
    migrées — la contrainte s'applique aux
    nouveaux rattachements).
    """

    if not chemin_projet:
        return None

    cible = _resoudre(chemin_projet)

    for dossier in dossiers_etudes:

        for nom, chemin in (
            reunions_des_etudes(dossier).items()
        ):

            if chemin and _resoudre(
                chemin
            ) == cible:
                return (str(dossier), nom)

    return None


def verifier_exclusivite(
    chemin_projet,
    dossiers_etudes,
    dossier_exclu=None
):
    """
    Vérifie l'invariant §9.1 AVANT un
    rattachement : retourne (dossier, nom) de
    l'étude qui référence déjà la réunion, ou
    None si elle est autonome.

    ``dossier_exclu`` : l'étude dans laquelle le
    rattachement est demandé (la réunion déjà
    référencée PAR CETTE étude n'est pas un
    conflit).
    """

    if dossier_exclu is not None:

        dossier_exclu = str(
            Path(dossier_exclu).resolve()
        )

    if not chemin_projet:
        return None

    cible = _resoudre(chemin_projet)

    for dossier in dossiers_etudes:

        if (
            dossier_exclu is not None
            and str(Path(dossier).resolve())
            == dossier_exclu
        ):
            continue

        for nom, chemin in (
            reunions_des_etudes(dossier).items()
        ):

            if chemin and _resoudre(
                chemin
            ) == cible:
                return (str(dossier), nom)

    return None


def rattacher(
    dossier_etude,
    chemin_projet,
    titre_1: str = "",
    etudes_connues=None
) -> str:
    """
    Rattache une réunion à une étude (référence,
    jamais copie), en fin d'ordre de lecture.

    L'exclusivité (invariant §9.1) est vérifiée
    AVANT l'écriture : si une autre étude
    référence déjà la réunion, l'opération est
    refusée (l'UI doit alors proposer un
    changement d'étude avec confirmation —
    ``changer_etude``).

    Retour : le nom de la réunion dans l'étude.
    """

    conflit = verifier_exclusivite(
        chemin_projet,
        etudes_connues or [],
        dossier_exclu=dossier_etude
    )

    if conflit is not None:
        raise RattachementError(
            "Cette réunion est déjà rattachée à "
            f"l'étude {conflit[0]} (réunion "
            f"« {conflit[1]} ») : une réunion "
            "appartient à une seule étude. "
            "Utilisez « Changer d'étude… » pour "
            "la déplacer."
        )

    etude_ouverte = ouvrir_etude(dossier_etude)

    #
    # P18.6-bis (spec correctifs §12) : la date
    # stockée est la date de RÉUNION (date de
    # l'audio), jamais la date technique de
    # rattachement.
    #
    from services.avancement import (
        date_audio_projet,
    )

    nom = ajouter_reunion(
        etude_ouverte,
        chemin_projet,
        titre_1=titre_1,
        date=date_audio_projet(chemin_projet)
    )

    sauvegarder_etude(etude_ouverte)

    return nom


def detacher_reunion(
    etude_ouverte: EtudeOuverte,
    nom: str
) -> None:
    """
    Détache une réunion de son étude SANS toucher
    aux traitements (option A de l'arbitrage,
    invariant §9.5) :

    - la référence (``reunions/<nom>.json``) et
      l'entrée d'ordre disparaissent ;
    - le découpage, les reformulations, le résumé
      et les entrées du registre FID RESTENT à
      l'ancienne étude (aucun déplacement, aucune
      copie, aucune suppression).

    Utilisé par le changement d'étude et par
    « Détacher de l'étude » (Gestion de l'étude).
    """

    if nom not in etude_ouverte.reunions:
        raise EtudeError(
            f"Réunion inconnue : {nom}"
        )

    dossier = etude_ouverte.dossier

    etude_ouverte.reunions.pop(nom, None)
    etude_ouverte.chemins_resolus.pop(nom, None)

    if nom in etude_ouverte.reunions_introuvables:
        etude_ouverte.reunions_introuvables.remove(
            nom
        )

    if nom in etude_ouverte.etude.ordre_reunions:
        etude_ouverte.etude.ordre_reunions.remove(
            nom
        )

    #
    # Option A : la référence seule disparaît.
    # Découpage, reformulations et résumé ne sont
    # NI retirés de la mémoire (ils restent
    # sauvés tels quels), NI supprimés du disque :
    # les traitements restent à l'ancienne étude.
    #

    (dossier / DOSSIER_REUNIONS
     / f"{nom}.json").unlink(missing_ok=True)


def changer_etude(
    dossier_source,
    nom: str,
    dossier_cible,
    etudes_connues=None
) -> str:
    """
    Changement d'étude (arbitrage, option A) :
    délie la réunion de son étude courante puis
    la rattache à l'étude cible. Les traitements
    déjà réalisés restent à l'ancienne étude —
    aucun déplacement, aucune copie
    (invariant §9.5).

    La confirmation est du ressort de l'UI.

    Retour : le nom de la réunion dans l'étude
    cible.
    """

    etude_source = ouvrir_etude(dossier_source)

    chemin = None

    reunion = etude_source.reunions.get(nom)

    if reunion is not None:

        resolu = (
            etude_source.chemins_resolus.get(nom)
        )

        if resolu is None:

            candidat = (
                Path(dossier_source)
                / reunion.chemin_projet
            )

            resolu = (
                candidat
                if candidat.exists()
                else reunion.chemin_absolu
            )

        chemin = resolu

    if chemin is None:
        raise RattachementError(
            "Réunion introuvable dans l'étude "
            "source : relocalisez-la avant de "
            "changer d'étude."
        )

    titre = reunion.titre_1 if reunion else ""

    detacher_reunion(etude_source, nom)
    sauvegarder_etude(etude_source)

    return rattacher(
        dossier_cible,
        chemin,
        titre_1=titre,
        etudes_connues=etudes_connues or []
    )


def _resoudre(chemin) -> str:
    """
    Normalise un chemin projet (fichier .sttproj
    ou dossier) pour la comparaison.
    """

    chemin = Path(chemin)

    if chemin.suffix == ".sttproj":
        chemin = chemin.parent

    try:
        return str(chemin.resolve())
    except OSError:
        return str(chemin)
