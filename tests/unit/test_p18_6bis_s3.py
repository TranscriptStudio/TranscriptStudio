"""
Tests P18.6-bis, SÉRIE 3 (spec
SPEC_NAVIGATION_MODIFS_V2_2026-10-30c §19 réécrit) :
stepper compact UNIQUEMENT après la transcription —
① Transcription → ② Reformulation → ③ Résumé →
④ Export ; pastille « Transcription » ouvrant
l'éditeur de correction (bleue pendant la
correction, verte une fois la diarisation
validée) ; mention discrète à la place du stepper
pour les réunions non transcrites (hub, page
Étude, page Réunion).

Invariants complémentaires couverts : 5, 8, 9.
"""

import json
import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
)

from services.avancement import (
    A_FAIRE,
    EN_COURS,
    ETAPES_ETUDE,
    ETAPES_REUNION,
    TERMINE,
    etapes_reunion,
    etapes_reunion_page_etude,
    etat_etape_transcription,
    transcrite,
)
from services.settings import SettingsManager
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
)


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


def ecrire_projet_sans_transcription(dossier):
    """
    Projet v1 sans mots horodatés (audio préparé
    non transcrit) : .sttproj lisible, words et
    blocks vides.
    """

    dossier.mkdir(parents=True, exist_ok=True)

    (dossier / "project.sttproj").write_text(
        json.dumps({
            "project_format_version": 1,
            "name": dossier.name,
            "audio_file": "",
            "transcription_id": None,
            "language_code": "fr",
            "duration_seconds": 10.0,
            "modified": False,
            "speakers": [],
            "words": [],
            "blocks": [],
            "original_elevenlabs_response": {},
        }, ensure_ascii=False),
        encoding="utf-8"
    )

    return dossier / "project.sttproj"


#
# ==================================================
# Service : transcription faite / pas faite.
# ==================================================
#

class TestServiceCompact:

    def test_transcrite(self, tmp_path):

        projet, projet_v1, _e, _n = (
            construire_etude_test(tmp_path)
        )

        assert transcrite(projet_v1)

        chemin = ecrire_projet_sans_transcription(
            tmp_path / "Audio_prepare"
        )

        from services.project_io import (
            load_project,
        )

        assert not transcrite(
            load_project(str(chemin))
        )

    def test_etats_compacts_none_si_non_transcrite(
        self,
        tmp_path
    ):

        chemin = ecrire_projet_sans_transcription(
            tmp_path / "Audio_prepare"
        )

        from services.project_io import (
            load_project,
        )

        projet = load_project(str(chemin))

        # Aucun stepper pour une réunion non
        # transcrite (invariant 9).
        assert etapes_reunion(
            projet
        ) is None

        assert etapes_reunion_page_etude(
            None,
            None,
            projet
        ) is None

    def test_pastille_transcription_bleue_puis_verte(
        self,
        tmp_path
    ):
        """
        §19 : la pastille « Transcription » est
        BLEUE tant que la correction est en cours
        (transcription sans diarisation), VERTE
        quand la transcription corrigée est validée
        (diarisation validée = blocs).
        """

        dossier = tmp_path / "En_correction"
        dossier.mkdir()

        # Transcription sans blocs : correction en
        # cours → bleue.
        (dossier / "project.sttproj").write_text(
            json.dumps({
                "project_format_version": 1,
                "name": "En correction",
                "audio_file": "",
                "transcription_id": "x",
                "language_code": "fr",
                "duration_seconds": 10.0,
                "modified": False,
                "speakers": [],
                "words": [
                    {
                        "text": "bonjour",
                        "start": 0.0,
                        "end": 1.0,
                        "speaker_id": "speaker_0",
                        "item_type": "word",
                    }
                ],
                "blocks": [],
                "original_elevenlabs_response": {},
            }, ensure_ascii=False),
            encoding="utf-8"
        )

        from services.project_io import (
            load_project,
        )

        projet = load_project(
            str(dossier / "project.sttproj")
        )

        assert etat_etape_transcription(
            projet
        ) == EN_COURS

        # Diarisation validée (blocs) : verte.
        _p, projet_v1, _e, _n = (
            construire_etude_test(tmp_path)
        )

        assert etat_etape_transcription(
            projet_v1
        ) == TERMINE

    def test_etats_compacts_transcrite(self, tmp_path):

        projet, projet_v1, etude, nom = (
            construire_etude_test(tmp_path)
        )

        etats = etapes_reunion(
            projet_v1,
            etude_ouverte=etude,
            nom=nom
        )

        # 4 étapes compactes (invariant 5 : jamais
        # Prétraitement / Transcription / Correction
        # séparés).
        assert tuple(etats.keys()) == ETAPES_REUNION

        assert "pretraitement" not in etats
        assert "correction" not in etats

        etude_etats = etapes_reunion_page_etude(
            etude,
            nom,
            projet_v1
        )

        # Page Étude : sans Export.
        assert tuple(etude_etats.keys()) == (
            ETAPES_ETUDE
        )

        assert "export" not in etude_etats


#
# ==================================================
# Page Réunion : pastille Transcription = éditeur
# (invariant 8) ; pas de stepper si non transcrite
# (invariant 9).
# ==================================================
#

class TestPageReunion:

    def test_pastille_transcription_ouvre_editeur(
        self,
        qapp,
        tmp_path
    ):
        """
        Invariant 8 : la pastille « Transcription »
        fusionnée ouvre TOUJOURS l'éditeur de
        correction.
        """

        projet, projet_v1, etude, nom = (
            construire_etude_test(tmp_path)
        )

        from ui.reunion_window import ReunionWindow

        fenetre = ReunionWindow(
            projet_v1,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            ),
            etude=etude,
            nom=nom
        )

        try:

            # Étape par défaut = pastille
            # Transcription = éditeur embarqué.
            assert (
                fenetre.etape_courante
                == "transcription"
            )

            from ui.main_window import MainWindow

            assert isinstance(
                fenetre.fenetre_correction,
                MainWindow
            )

            # Depuis une autre étape, la pastille
            # ramène TOUJOURS à l'éditeur.
            fenetre.changer_etape("export")
            fenetre.changer_etape("transcription")

            assert (
                fenetre.etape_courante
                == "transcription"
            )

            assert isinstance(
                fenetre.contenu.currentWidget(),
                MainWindow
            )

        finally:
            fenetre.close()

    def test_non_transcrite_sans_stepper(
        self,
        qapp,
        tmp_path
    ):
        """
        Invariant 9 : une réunion non transcrite
        n'affiche JAMAIS de stepper — mention
        discrète à la place.
        """

        chemin = ecrire_projet_sans_transcription(
            tmp_path / "Audio_prepare"
        )

        from services.project_io import (
            load_project,
        )
        from ui.reunion_window import ReunionWindow

        projet = load_project(str(chemin))

        fenetre = ReunionWindow(
            projet,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            assert not fenetre.stepper.isVisibleTo(
                fenetre
            )

            assert (
                fenetre.mention_label.text()
                == "transcription en attente"
            )

            assert fenetre.mention_label.isVisibleTo(
                fenetre
            )

        finally:
            fenetre.close()


#
# ==================================================
# Hub et page Étude : mention au lieu du stepper
# pour une réunion non transcrite (invariant 9).
# ==================================================
#

class TestMentions:

    def test_hub_mention_non_transcrite(
        self,
        qapp,
        tmp_path
    ):

        chemin = ecrire_projet_sans_transcription(
            tmp_path / "Audio_prepare"
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.add_recent_project(str(chemin))

        from unittest.mock import patch

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from ui.home_window import HomeWindow

        with patch(
            "services.llm.catalogue"
            ".charger_catalogue",
            return_value=catalogue_par_defaut(),
        ):
            accueil = HomeWindow(settings=settings)

        try:

            from ui.stepper import StepperBar

            assert not (
                accueil
                .dernieres_conteneur
                .findChildren(StepperBar)
            )

            mentions = [
                l.text()
                for l in (
                    accueil.findChildren(QLabel)
                )
                if l.text()
                == "transcription en attente"
            ]

            assert mentions

        finally:
            accueil.close()

    def test_etude_mention_non_transcrite(
        self,
        qapp,
        tmp_path
    ):
        """
        Une réunion non transcrite attachée à une
        étude affiche la mention, pas de stepper ;
        une réunion transcrite affiche le stepper
        compact (sans Export).
        """

        projet, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        chemin = ecrire_projet_sans_transcription(
            tmp_path / "Audio_prepare"
        )

        from services.etude_io import (
            ajouter_reunion,
            sauvegarder_etude,
        )

        ajouter_reunion(
            etude,
            tmp_path / "Audio_prepare",
            titre_1="Audio préparé"
        )

        sauvegarder_etude(etude)

        from ui.etude_window import EtudeWindow

        page = EtudeWindow(
            tmp_path / "Etude",
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            from ui.stepper import StepperBar

            steppers = (
                page.reunions_liste
                .findChildren(StepperBar)
            )

            # Une seule réunion transcrite : un seul
            # stepper, 3 pastilles sans Export.
            assert len(steppers) == 1

            assert len(steppers[0].boutons) == 3

            libelles = [
                b.text()
                for b in (
                    steppers[0].boutons.values()
                )
            ]

            assert libelles == [
                "① Transcription",
                "② Reformulation",
                "③ Résumé",
            ]

            # La réunion non transcrite : mention.
            mentions = [
                l.text()
                for l in (
                    page.reunions_liste
                    .findChildren(QLabel)
                )
                if l.text()
                == "transcription en attente"
            ]

            assert mentions

        finally:
            page.close()


#
# ==================================================
# §19 : transcrire un audio déjà prétraité =
# transcription directe.
# ==================================================
#

class TestDejaPretraite:

    def test_trouver_projet_prepare(self, tmp_path):
        """
        Un audio déjà prétraité lors d'une session
        précédente (copie de l'audio + audio
        finalisé + journal, sans transcription) est
        retrouvé : la transcription reprendra
        DIRECTEMENT, sans nouvelle étape de
        prétraitement.
        """

        import json
        from pathlib import Path

        from services.project_manager import (
            ProjectManager,
        )

        manager = ProjectManager()

        # Racine isolée pour le test.
        manager.root = tmp_path

        audio = tmp_path / "reunion.mp3"
        audio.write_bytes(b"audio")

        # Dossier déjà prétraité, non transcrit.
        prepare = (
            tmp_path / "Commun"
            / "2026-10-01_reunion"
        )
        prepare.mkdir(parents=True)

        (prepare / "reunion.mp3").write_bytes(
            b"audio"
        )

        (prepare / "audio_processed.wav").write_bytes(
            b"RIFF...."
        )

        (prepare / "journal_operations.json").write_text(
            json.dumps({"operations": []}),
            encoding="utf-8"
        )

        # Dossier déjà TRANSCRIT : pas un audio en
        # attente.
        transcrit = (
            tmp_path / "Commun"
            / "2026-10-02_reunion"
        )
        transcrit.mkdir(parents=True)

        (transcrit / "reunion.mp3").write_bytes(
            b"audio"
        )

        (transcrit / "audio_processed.wav").write_bytes(
            b"RIFF...."
        )

        (transcrit / "journal_operations.json").write_text(
            json.dumps({"operations": []}),
            encoding="utf-8"
        )

        (transcrit / "project.sttproj").write_text(
            "{}",
            encoding="utf-8"
        )

        # Audio inconnu : rien.
        autre = tmp_path / "autre.mp3"
        autre.write_bytes(b"autre")

        assert manager.trouver_projet_prepare(
            str(autre)
        ) is None

        # L'audio déjà prétraité (non transcrit) est
        # retrouvé, pas le transcrit.
        trouve = manager.trouver_projet_prepare(
            str(audio)
        )

        assert trouve == prepare
