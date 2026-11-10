# tests/unit/test_p18_8d_badge.py
"""
P18.8d — Badge « Bible » de la page Étude : version
commune aux réunions rattachées, « Bibles mixtes » si
divergence (info-bulle listant les versions par réunion
— ARBITRAGE_P18_7_ECARTS 2026-11-09a, écart 3).
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.qt

from services.bibles import (
    version_commune_etude,
    versions_bibles_reunions,
)
from services.etude_io import (
    ajouter_reunion,
    ajouter_version_reformulation,
    attribuer_fid,
    creer_etude,
    sauvegarder_etude,
)
from services.settings import SettingsManager


def creer_projet_v1(dossier_parent: Path, nom: str) -> Path:
    dossier = dossier_parent / nom
    dossier.mkdir(parents=True)

    (dossier / "project.sttproj").write_text(
        json.dumps({
            "project_format_version": 1,
            "name": nom,
            "audio_file": "audio.wav",
            "transcription_id": None,
            "language_code": "fr",
            "duration_seconds": 100.0,
            "modified": False,
            "speakers": [],
            "words": [],
            "blocks": [],
            "original_elevenlabs_response": {},
        }),
        encoding="utf-8"
    )

    return dossier


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def page(qapp, tmp_path):
    from ui.etude_window import EtudeWindow

    etude = creer_etude(tmp_path / "Etude", "Évangile de Luc")

    noms = []

    for nom_dossier in ("2026-10-13_Luc1b", "2026-10-20_Luc2a"):
        projet = creer_projet_v1(tmp_path, nom_dossier)
        nom = ajouter_reunion(etude, projet, "Chapitre")
        noms.append(nom)

    sauvegarder_etude(etude)

    settings = SettingsManager(str(tmp_path / "reglages"))

    fenetre = EtudeWindow(
        tmp_path / "Etude",
        settings=settings
    )

    yield fenetre, tmp_path, noms

    fenetre.close()


class TestBadgeBible:

    def test_badge_version_commune(self, page):
        fenetre, tmp_path, noms = page

        # Toutes les réunions sur darbyR (défaut).
        # P18.9c : badge simplifié, JAMAIS de champ
        # « versification » distinct.
        assert fenetre._texte_badge_bible() == (
            "Bible : Darby révisée"
        )

        assert "versification" not in (
            fenetre._texte_badge_bible()
        )

        tooltip = fenetre._tooltip_badge_bible()

        assert "commune" in tooltip
        # Info-bulle épurée : aucun commentaire de
        # spec (P18.9c, invariant 4).
        assert "P18.5" not in tooltip
        assert "versification" not in tooltip.lower()

    def test_badge_bibles_mixtes(self, page):
        fenetre, tmp_path, noms = page

        # Fait diverger une réunion (sur l'étude de la
        # fenêtre, rouverte depuis le disque).
        fenetre.etude.tier_de(noms[1]).parametres.bible[
            "version"
        ] = "segond1910"

        assert fenetre._texte_badge_bible() == "Bibles mixtes"

        tooltip = fenetre._tooltip_badge_bible()

        assert "Segond 1910" in tooltip
        assert "Darby révisée" in tooltip
        # Liste par réunion (titre_1 = « Chapitre »).
        assert tooltip.count("Chapitre") == 2

    def test_helpers_bibles(self, page):
        fenetre, tmp_path, noms = page

        versions = versions_bibles_reunions(fenetre.etude)
        assert versions == {noms[0]: "darbyR", noms[1]: "darbyR"}

        version, mixte = version_commune_etude(fenetre.etude)
        assert version == "darbyR"
        assert mixte is False

        fenetre.etude.tier_de(noms[0]).parametres.bible[
            "version"
        ] = "darby"

        version, mixte = version_commune_etude(fenetre.etude)
        assert mixte is True
