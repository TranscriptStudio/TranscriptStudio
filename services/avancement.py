# services/avancement.py
"""
Avancement d'une réunion : états des étapes
①→⑥ du stepper (P18.6, spec navigation §3).

États possibles d'une étape :

- ``a_faire`` : gris (rien de fait) ;
- ``en_cours`` : bleu (commencé, pas terminé) ;
- ``termine`` : vert (terminé).

Définitions retenues (testées unitairement,
invariants §9.3 et §9.4 de la spéc) :

- ① Prétraitement : terminé si le dossier du
  projet v1 contient un journal des opérations
  de prétraitement (``journal_operations.json``,
  P14.1) ; à faire sinon (un audio importé sans
  prétraitement reste gris) ;
- ② Transcription : terminé si le projet
  contient des mots horodatés ;
- ③ Correction : terminé si le projet contient
  des blocs de diarisation (la correction aboutit
  à une diarisation validée), en cours si la
  transcription existe sans bloc ;
- ④ Reformulation (optionnelle) : terminé si
  tous les blocs actifs de la réunion ont une
  version validée ; en cours si certains
  résultats existent sans tout valider ;
- ⑤ Résumé (optionnelle) : terminé si le résumé
  de la réunion est validé ; en cours si des
  versions existent sans validation ;
- ⑥ Export : terminé si un export de réunion a
  été enregistré dans les réglages
  (trace d'export, jamais dans le projet v1).

L'affichage d'avancement de la page Étude
n'expose JAMAIS l'étape ⑥ (invariant §9.4) :
l'objectif final d'une étude est l'export global
de l'ouvrage, pas l'export de réunion.
"""

from pathlib import Path

A_FAIRE = "a_faire"
EN_COURS = "en_cours"
TERMINE = "termine"

ETAPE_PRETRAITEMENT = "pretraitement"
ETAPE_TRANSCRIPTION = "transcription"
ETAPE_CORRECTION = "correction"
ETAPE_REFORMULATION = "reformulation"
ETAPE_RESUME = "resume"
ETAPE_EXPORT = "export"

#
# Modèle COMPACT (P18.6-bis, spec correctifs §19) :
# le stepper n'apparaît qu'UNE FOIS LA
# TRANSCRIPTION RÉALISÉE — Transcription →
# Reformulation → Résumé → Export (①→④). Les
# étapes Prétraitement / Transcription /
# Correction n'apparaissent PLUS séparément : la
# pastille « Transcription » fusionne
# transcription + correction et OUVRE l'éditeur
# de correction (invariants complémentaires 5 et
# 8). Une réunion non transcrite n'affiche
# JAMAIS de stepper (invariant 9) : mention
# discrète à la place.
#
ETAPES_REUNION = (
    ETAPE_TRANSCRIPTION,
    ETAPE_REFORMULATION,
    ETAPE_RESUME,
    ETAPE_EXPORT,
)

# Page Étude : avancement SANS Export (l'objectif
# final d'une étude est l'export global de
# l'ouvrage, spec §4.2).
ETAPES_ETUDE = (
    ETAPE_TRANSCRIPTION,
    ETAPE_REFORMULATION,
    ETAPE_RESUME,
)

# Reformulation et Résumé restent optionnelles :
# l'optionnalité ne se lit que dans le bouton
# « Étape suivante : … (optionnelle) » et
# l'info-bulle (P18.6-bis §18).
ETAPES_OPTIONNELLES = (
    ETAPE_REFORMULATION,
    ETAPE_RESUME,
)

LIBELLES_ETAPES = {
    ETAPE_TRANSCRIPTION: "① Transcription",
    ETAPE_REFORMULATION: "② Reformulation",
    ETAPE_RESUME: "③ Résumé",
    ETAPE_EXPORT: "④ Export",
}

# Mention discrète d'une réunion non transcrite
# (stepper absent, spec correctifs §19 ; la
# transcription active est couverte par le
# dialogue de progression du hub).
MENTION_NON_TRANCRITE = "transcription en attente"

FICHIER_JOURNAL_PRETRAITEMENT = (
    "journal_operations.json"
)


def date_audio_projet(chemin_projet):
    """
    Date de l'audio d'un projet v1 (P18.6-bis,
    spec correctifs §12, invariant complémentaire
    4) : lecture légère du .sttproj, résolution du
    fichier audio, date = mtime de l'audio au
    format ``AAAA-MM-JJ``.

    Retourne None si la date n'est pas déterminable
    (pas d'audio, fichier absent).
    """

    import json
    import os

    chemin = Path(chemin_projet)

    if chemin.is_dir():
        chemin = chemin / "project.sttproj"

    if not chemin.is_file():
        return None

    try:

        with open(
            chemin,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

    except (OSError, ValueError):
        return None

    audio = data.get("audio_file")

    if not audio:
        return None

    dossier = chemin.parent

    fichier = Path(audio)

    if not fichier.is_absolute():
        fichier = dossier / fichier

    if not fichier.is_file():
        return None

    try:
        mtime = os.path.getmtime(fichier)
    except OSError:
        return None

    import datetime

    return datetime.datetime.fromtimestamp(
        mtime
    ).strftime("%Y-%m-%d")


def date_reunion(
    projet,
    reunion=None
) -> str:
    """
    Date de réunion AFFICHÉE : toujours la date de
    l'audio (date de réunion), jamais une date
    technique de rattachement. Repli : date stockée
    de la réunion (elle-même alimentée à la date de
    l'audio depuis P18.6-bis), sinon chaîne vide.
    """

    chemin = getattr(
        projet,
        "project_file",
        None
    )

    if chemin:

        audio = date_audio_projet(chemin)

        if audio:
            return audio

    if reunion is not None:

        date_stockee = getattr(
            reunion,
            "date",
            ""
        )

        if date_stockee:
            return date_stockee

    return ""


def etat_pretraitement(projet) -> str:
    """
    ① Prétraitement : vert si le dossier du projet
    v1 contient le journal des opérations (le
    prétraitement a été réalisé), gris sinon.
    """

    dossier = _dossier_projet(projet)

    if dossier is None:
        return A_FAIRE

    if (
        dossier / FICHIER_JOURNAL_PRETRAITEMENT
    ).is_file():
        return TERMINE

    return A_FAIRE


def etat_transcription(projet) -> str:
    """
    ② Transcription : vert si le projet contient
    des mots horodatés.
    """

    if projet is None:
        return A_FAIRE

    if getattr(projet, "words", None):
        return TERMINE

    return A_FAIRE


def etat_correction(projet) -> str:
    """
    ③ Correction : vert si le projet contient des
    blocs de diarisation (la correction aboutit à
    une diarisation validée) ; bleu si la
    transcription existe sans bloc ; gris sinon.
    """

    if projet is None:
        return A_FAIRE

    if getattr(projet, "blocks", None):
        return TERMINE

    if getattr(projet, "words", None):
        return EN_COURS

    return A_FAIRE


def etat_reformulation(etude_ouverte, nom) -> str:
    """
    ④ Reformulation (optionnelle) : vert si tous
    les blocs actifs de la réunion ont une version
    validée ; bleu si des résultats existent sans
    tout valider ; gris sinon (sans étude ou sans
    segmentation, l'étape reste à faire —
    l'utilisateur peut la passer).
    """

    if etude_ouverte is None or nom is None:
        return A_FAIRE

    decoupage = etude_ouverte.decoupages.get(nom)

    if decoupage is None:
        return A_FAIRE

    fids = _fids_reunion(etude_ouverte, nom)

    if not fids:
        return A_FAIRE

    validees = 0
    avec_resultat = 0

    for fid in fids:

        resultat = (
            etude_ouverte.reformulations.get(fid)
        )

        if resultat is None:
            continue

        avec_resultat += 1

        if any(
            version.validation is not None
            for version in resultat.versions
        ):
            validees += 1

    if validees == len(fids):
        return TERMINE

    if avec_resultat:
        return EN_COURS

    return A_FAIRE


def etat_resume(etude_ouverte, nom) -> str:
    """
    ⑤ Résumé (optionnelle) : vert si le résumé de
    la réunion est validé ; bleu si des versions
    existent sans validation ; gris sinon.
    """

    if etude_ouverte is None or nom is None:
        return A_FAIRE

    reunion = etude_ouverte.reunions.get(nom)

    if reunion is None:
        return A_FAIRE

    if reunion.resume_valide:
        return TERMINE

    resultat = etude_ouverte.resumes.get(nom)

    if resultat is not None and resultat.versions:
        return EN_COURS

    return A_FAIRE


def etat_export(chemin_projet, settings=None) -> str:
    """
    ⑥ Export : vert si un export de cette réunion
    a été enregistré dans les réglages (trace
    d'export — le projet v1 n'est jamais modifié).
    """

    if settings is None or not chemin_projet:
        return A_FAIRE

    chemin = str(Path(chemin_projet).resolve())

    exports = settings.settings.get(
        "exports_reunions",
        []
    )

    if chemin in exports:
        return TERMINE

    return A_FAIRE


def transcrite(projet) -> bool:
    """
    La transcription de la réunion est-elle
    réalisée (mots horodatés présents) ?

    P18.6-bis (spec correctifs §19) : une réunion
    sans transcription est un audio préparé non
    transcrit — elle n'affiche JAMAIS de stepper
    (invariant complémentaire 9), le déroulement
    de préparation audio est linéaire.
    """

    return bool(
        getattr(projet, "words", None)
    )


def etat_etape_transcription(projet) -> str:
    """
    État de la pastille « Transcription » (fusion
    transcription + correction, spec correctifs
    §19) :

    - VERTE quand la transcription corrigée est
      validée — concrètement : la diarisation est
      validée (blocs de parole présents, aboutissement
      de la correction dans l'éditeur) ;
    - BLEUE tant que la correction est en cours
      (transcription sans blocs) ;
    - grise sinon (pas de stepper du tout dans ce
      cas, la réunion n'est pas transcrite).
    """

    return etat_correction(projet)


def etats_compacts(
    projet,
    etude_ouverte=None,
    nom=None,
    settings=None,
    chemin_projet=None
) -> dict:
    """
    États des QUATRE étapes compactes d'une réunion
    TRANSCRITE (hub et page Réunion, spec
    correctifs §19) : ① Transcription →
    ② Reformulation → ③ Résumé → ④ Export.

    Pour une réunion NON transcrite, retourne
    None : aucun stepper (invariant 9 — mention
    discrète à la place).
    """

    if not transcrite(projet):
        return None

    if chemin_projet is None:
        chemin_projet = getattr(
            projet,
            "project_file",
            None
        )

    return {
        ETAPE_TRANSCRIPTION: (
            etat_etape_transcription(projet)
        ),
        ETAPE_REFORMULATION: (
            etat_reformulation(etude_ouverte, nom)
        ),
        ETAPE_RESUME: (
            etat_resume(etude_ouverte, nom)
        ),
        ETAPE_EXPORT: (
            etat_export(chemin_projet, settings)
        ),
    }


def etapes_reunion(
    projet,
    etude_ouverte=None,
    nom=None,
    settings=None,
    chemin_projet=None
) -> dict:
    """
    Alias historique : états du stepper compact de
    la page Réunion (P18.6-bis §19). Retourne None
    pour une réunion non transcrite (aucun
    stepper).
    """

    return etats_compacts(
        projet,
        etude_ouverte=etude_ouverte,
        nom=nom,
        settings=settings,
        chemin_projet=chemin_projet
    )


def etapes_reunion_page_etude(
    etude_ouverte,
    nom,
    projet
) -> dict:
    """
    États d'avancement d'une réunion AFFICHÉS SUR
    LA PAGE ÉTUDE : Transcription → Reformulation
    → Résumé, JAMAIS Export (invariant §9.4 —
    l'objectif d'une étude est l'export global de
    l'ouvrage, pas l'export de réunion). Retourne
    None pour une réunion non transcrite (aucun
    stepper, invariant complémentaire 9).
    """

    etats = etapes_reunion(
        projet,
        etude_ouverte=etude_ouverte,
        nom=nom,
        settings=None,
    )

    if etats is None:
        return None

    etats.pop(ETAPE_EXPORT)

    return etats


def etapes_etude() -> tuple:
    """
    Liste des étapes affichées par la page Étude
    (invariant §9.4 : jamais l'étape ⑥).
    """

    return ETAPES_ETUDE


def cout_reunion(etude_ouverte, nom) -> float:
    """
    Coût cumulé des traitements LLM d'une réunion :
    somme des coûts estimés de toutes les versions
    de reformulation de ses blocs et de ses
    versions de résumé (les éditions manuelles,
    sans LLM, portent stats None : coût nul).
    """

    if etude_ouverte is None or nom is None:
        return 0.0

    total = 0.0

    for fid in _fids_reunion(etude_ouverte, nom):

        resultat = (
            etude_ouverte.reformulations.get(fid)
        )

        if resultat is None:
            continue

        for version in resultat.versions:

            if version.stats:
                total += (
                    version.stats.get(
                        "cout_estime",
                        0.0
                    )
                    or 0.0
                )

    resultat_resume = (
        etude_ouverte.resumes.get(nom)
    )

    if resultat_resume is not None:

        for version in resultat_resume.versions:

            if version.stats:
                total += (
                    version.stats.get(
                        "cout_estime",
                        0.0
                    )
                    or 0.0
                )

    return total


def _dossier_projet(projet):
    """
    Dossier du projet v1 (None si indisponible).
    """

    if projet is None:
        return None

    chemin = getattr(
        projet,
        "project_file",
        None
    )

    if not chemin:
        return None

    return Path(chemin).parent


def _fids_reunion(etude_ouverte, nom) -> list:
    """
    FID actifs de la réunion (blocs de la
    segmentation dont le FID est actif au
    registre).
    """

    from services.decoupage import blocs_actifs

    try:
        return [
            bloc.fid
            for bloc in blocs_actifs(
                etude_ouverte,
                nom
            )
        ]
    except Exception:
        return []
