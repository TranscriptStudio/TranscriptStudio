# tests/unit/test_p18_8c_bible.py
"""
P18.8c — Sélecteur de version de la Bible dans les
paramètres de l'étude : à l'enregistrement, la version
choisie PROPAGE vers les tiers de toutes les réunions
rattachées (ARBITRAGE_P18_7_ECARTS 2026-11-09a, écarts
2 et 3), avec libellé explicite (jamais silencieux) et
avertissement de versification au changement (écart =
information, jamais de ré-alignement automatique —
BIBLE_JND_V2).


"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.qt

from services.bibles import (
    VERSIONS_BIBLE,
    version_bible_etude,
    version_commune_etude,
    versions_bibles_reunions,
)
from services.etude_io import (
    ajouter_reunion,
    attribuer_fid,
    ajouter_version_reformulation,
    creer_etude,
    ouvrir_etude,
    sauvegarder_etude,
)
from services.settings import SettingsManager
from services.tier_reunion import (
    ouvrir_tier,
)
from tests.unit.test_reformulation_ui import (
    construire_projet_test,
)


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
def etude_deux_reunions(tmp_path):
    """
    Étude v2 à DEUX réunions rattachées, chacune avec
    un bloc reformulé (pour vérifier qu'aucun
    ré-alignement n'a lieu).
    """

    etude = creer_etude(tmp_path / "Etude", "Évangile de Luc")

    noms = []

    for nom_dossier in ("2026-10-13_Luc1b", "2026-10-20_Luc2a"):
        projet = creer_projet_v1(tmp_path, nom_dossier)
        nom = ajouter_reunion(etude, projet, "Chapitre")
        noms.append(nom)

        fid = attribuer_fid(etude, nom)
        ajouter_version_reformulation(
            etude, nom, fid, f"Reformulation {nom}."
        )

    sauvegarder_etude(etude)

    return etude, noms, tmp_path


@pytest.fixture
def page(qapp, tmp_path, etude_deux_reunions):
    from ui.etude_window import EtudeWindow

    etude, noms, tmp_path = etude_deux_reunions

    settings = SettingsManager(str(tmp_path / "reglages"))

    fenetre = EtudeWindow(
        tmp_path / "Etude",
        settings=settings
    )

    yield fenetre, tmp_path, etude, noms

    fenetre.close()


class TestPropagationBible:

    def test_libelle_explicite_propagation(self, page):
        """
        Écart 2 (ARBITRAGE_P18_7_ECARTS) : le dialogue
        affiche un libellé EXPLICITE indiquant que
        l'enregistrement propage la version vers les
        tiers des réunions rattachées — jamais silencieux.
        """

        from ui.parametres_etude_dialog import (
            ParametresEtudeDialog,
        )

        fenetre, tmp_path, etude, noms = page

        dialogue = ParametresEtudeDialog(
            fenetre.etude,
            parent=fenetre
        )

        texte = dialogue.propagation_label.text()

        assert "propagée" in texte
        assert "2 réunion" in texte
        assert "tiers" in texte

        dialogue.close()

    def test_enregistrement_propage_vers_les_tiers(
        self, page, qapp
    ):
        """
        P18.8c : à l'enregistrement, la version choisie
        propage vers le tier de CHAQUE réunion rattachée
        (persisté sur disque).
        """

        from ui.parametres_etude_dialog import (
            ParametresEtudeDialog,
        )

        fenetre, tmp_path, etude, noms = page

        dialogue = ParametresEtudeDialog(
            fenetre.etude,
            parent=fenetre
        )

        # Choisit segond1910 (versification différente).
        index = dialogue.version_bible_combo.findData(
            "segond1910"
        )
        assert index >= 0
        dialogue.version_bible_combo.setCurrentIndex(index)

        with patch(
            "PySide6.QtWidgets.QMessageBox.warning"
        ) as avert:
            with patch(
                "PySide6.QtWidgets.QMessageBox.question",
                staticmethod(lambda *a, **k: 0)
            ):
                dialogue.enregistrer()

        # Avertissement de versification affiché
        # (darbyR → segond1910 : versifications différentes).
        assert avert.called

        # Propagé dans les DEUX tiers, persisté.
        for nom in noms:
            projet = tmp_path / nom
            tier = ouvrir_tier(projet)
            assert (
                tier.parametres.bible["version"]
                == "segond1910"
            )

        # Relu après réouverture.
        relue = ouvrir_etude(tmp_path / "Etude")

        for nom in noms:
            assert (
                relue.tier_de(nom).parametres.bible[
                    "version"
                ]
                == "segond1910"
            )

        version, mixte = version_commune_etude(relue)
        assert version == "segond1910"
        assert mixte is False

        dialogue.close()

    def test_pas_d_avertissement_meme_versification(
        self, page, qapp
    ):
        """
        darby → darbyR : même versification « Darby » →
        PAS d'avertissement de versification.
        """

        from ui.parametres_etude_dialog import (
            ParametresEtudeDialog,
        )

        fenetre, tmp_path, etude, noms = page

        # Tiers réglés sur darby (même versification que
        # darbyR).
        for nom in noms:
            etude.tier_de(nom).parametres.bible[
                "version"
            ] = "darby"

        dialogue = ParametresEtudeDialog(
            fenetre.etude,
            parent=fenetre
        )

        index = dialogue.version_bible_combo.findData("darbyR")
        dialogue.version_bible_combo.setCurrentIndex(index)

        with patch(
            "PySide6.QtWidgets.QMessageBox.warning"
        ) as avert:
            with patch(
                "PySide6.QtWidgets.QMessageBox.question",
                staticmethod(lambda *a, **k: 0)
            ):
                dialogue.enregistrer()

        assert not avert.called

        dialogue.close()

    def testJamaisDeRealignementAutomatique(self, page, qapp):
        """
        BIBLE_JND_V2 §4.5 : changer la version ne
        re-traite rien — les reformulations sont
        inchangées.
        """

        from ui.parametres_etude_dialog import (
            ParametresEtudeDialog,
        )

        fenetre, tmp_path, etude, noms = page

        avant = {
            nom: {
                fid: r.versions[-1].texte
                for fid, r in (
                    etude.tier_de(nom).reformulations.items()
                )
            }
            for nom in noms
        }

        dialogue = ParametresEtudeDialog(
            fenetre.etude,
            parent=fenetre
        )

        index = dialogue.version_bible_combo.findData(
            "segond1910"
        )
        dialogue.version_bible_combo.setCurrentIndex(index)

        with patch(
            "PySide6.QtWidgets.QMessageBox.warning"
        ), patch(
            "PySide6.QtWidgets.QMessageBox.question",
            staticmethod(lambda *a, **k: 0)
        ):
            dialogue.enregistrer()

        dialogue.close()

        apres = {
            nom: {
                fid: r.versions[-1].texte
                for fid, r in (
                    etude.tier_de(nom).reformulations.items()
                )
            }
            for nom in noms
        }

        assert avant == apres


