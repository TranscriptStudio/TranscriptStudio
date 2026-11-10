# tests/unit/test_p18_8d_badge.py
"""
P18.8d — Badge « Bible » : version commune aux
réunions rattachées, « Bibles mixtes » si divergence
(info-bulle listant les versions par réunion —
ARBITRAGE_P18_7_ECARTS 2026-11-09a, écart 3).

P18.9-bis.c (relecture 2 du 10/11) : le badge n'est
PLUS affiché sur la page Étude — la page n'affiche
plus aucune version de Bible (ni badge d'en-tête, ni
mention sous la synthèse). Les helpers de calcul
restent testés ici.
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

    def test_page_etude_sans_aucune_mention_bible(self, page):
        """
        P18.9-bis.c (amende P18.8d/P18.9c) : la page
        Étude n'affiche PLUS aucune version de Bible —
        ni badge d'en-tête, ni mention sous la synthèse.
        """

        fenetre, tmp_path, noms = page

        assert not hasattr(fenetre, "badge_bible_label")

        # Aucun label de la page ne mentionne une Bible.
        from PySide6.QtWidgets import QLabel

        textes = [
            label.text()
            for label in fenetre.findChildren(QLabel)
        ]

        assert not any(
            "Bible" in texte for texte in textes
        )

    def test_badge_version_commune(self, page):
        """
        Le calcul du badge (service) reste disponible —
        il n'est simplement plus affiché sur la page
        Étude (P18.9-bis.c) : version commune, JAMAIS de
        champ « versification » distinct ; info-bulle
        épurée.
        """

        from services.bibles import badge_bible_etude

        fenetre, tmp_path, noms = page

        # Toutes les réunions sur darbyR (défaut).
        texte, tooltip = badge_bible_etude(fenetre.etude)

        assert texte == "Bible : Darby révisée"

        assert "versification" not in texte
        assert "commune" in tooltip
        # Info-bulle épurée : aucun commentaire de
        # spec (P18.9c, invariant 4).
        assert "P18.5" not in tooltip
        assert "versification" not in tooltip.lower()

    def test_badge_bibles_mixtes(self, page):
        """
        « Bibles mixtes » quand les tiers divergent
        (service ; plus affiché sur la page Étude,
        P18.9-bis.c).
        """

        from services.bibles import badge_bible_etude

        fenetre, tmp_path, noms = page

        # Fait diverger une réunion (sur l'étude de la
        # fenêtre, rouverte depuis le disque).
        fenetre.etude.tier_de(noms[1]).parametres.bible[
            "version"
        ] = "segond1910"

        texte, tooltip = badge_bible_etude(fenetre.etude)

        assert texte == "Bibles mixtes"

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
