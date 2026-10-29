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

ETAPES_REUNION = (
    ETAPE_PRETRAITEMENT,
    ETAPE_TRANSCRIPTION,
    ETAPE_CORRECTION,
    ETAPE_REFORMULATION,
    ETAPE_RESUME,
    ETAPE_EXPORT,
)

# Page Étude : avancement ①→⑤ sans ⑥ (spec §4.2).
ETAPES_ETUDE = ETAPES_REUNION[:5]

# ④ et ⑤ sont optionnelles (spec §3.3) : contour
# pointillé, passage direct ②→⑥ toujours possible.
ETAPES_OPTIONNELLES = (
    ETAPE_REFORMULATION,
    ETAPE_RESUME,
)

LIBELLES_ETAPES = {
    ETAPE_PRETRAITEMENT: "① Prétraitement",
    ETAPE_TRANSCRIPTION: "② Transcription",
    ETAPE_CORRECTION: "③ Correction",
    ETAPE_REFORMULATION: "④ Reformulation",
    ETAPE_RESUME: "⑤ Résumé",
    ETAPE_EXPORT: "⑥ Export",
}

FICHIER_JOURNAL_PRETRAITEMENT = (
    "journal_operations.json"
)


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


def etapes_reunion(
    projet,
    etude_ouverte=None,
    nom=None,
    settings=None,
    chemin_projet=None
) -> dict:
    """
    États des six étapes d'une réunion (hub et page
    Réunion — le stepper complet ①→⑥ y figure,
    spec §2.4 et §3.2).
    """

    if chemin_projet is None:
        chemin_projet = getattr(
            projet,
            "project_file",
            None
        )

    return {
        ETAPE_PRETRAITEMENT: (
            etat_pretraitement(projet)
        ),
        ETAPE_TRANSCRIPTION: (
            etat_transcription(projet)
        ),
        ETAPE_CORRECTION: (
            etat_correction(projet)
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


def etapes_reunion_page_etude(
    etude_ouverte,
    nom,
    projet
) -> dict:
    """
    États d'avancement d'une réunion AFFICHÉS SUR
    LA PAGE ÉTUDE : ①→⑤, jamais ⑥ (invariant
    §9.4 — l'objectif d'une étude est l'export
    global de l'ouvrage, pas l'export de réunion).
    """

    etats = etapes_reunion(
        projet,
        etude_ouverte=etude_ouverte,
        nom=nom,
        settings=None,
    )

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
