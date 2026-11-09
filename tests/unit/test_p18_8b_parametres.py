# tests/unit/test_p18_8b_parametres.py
"""
P18.8b — Bouton « Paramètres de l'étude » (page Étude,
anciennement « Modifier l'étude ») : ouvre le dialogue
des paramètres de l'étude, qui comporte désormais un
bloc Général (titre + thème), persistés.
"""

import pytest

pytestmark = pytest.mark.qt

from services.etude_io import (
    creer_etude,
    ouvrir_etude,
)
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
)


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def page(qapp, tmp_path):
    from services.settings import SettingsManager
    from ui.etude_window import EtudeWindow

    _p, _pv, etude, _nom = construire_etude_test(tmp_path)

    settings = SettingsManager(str(tmp_path / "reglages"))

    fenetre = EtudeWindow(
        tmp_path / "Etude",
        settings=settings
    )

    yield fenetre, tmp_path, settings

    fenetre.close()


class TestBoutonParametres:

    def test_libelle_bouton(self, page):
        fenetre, _tmp, _s = page

        assert (
            fenetre.modifier_button.text()
            == "Paramètres de l'étude"
        )

    def test_ouvre_dialogue_parametres(self, page, qapp):
        from unittest.mock import patch

        fenetre, _tmp, _s = page

        appele = {}

        class DialogueFictif:

            def __init__(self, etude_ouverte, parent=None):
                appele["ouvert"] = True
                appele["etude"] = etude_ouverte

            def exec(self):
                return False

        with patch(
            "ui.parametres_etude_dialog"
            ".ParametresEtudeDialog",
            DialogueFictif
        ):
            fenetre.modifier_etude()

        assert appele.get("ouvert")
        assert appele["etude"] is fenetre.etude


class TestBlocGeneral:

    def test_bloc_general_titre_theme(self, page, qapp):
        from ui.parametres_etude_dialog import (
            ParametresEtudeDialog,
        )

        fenetre, tmp_path, _s = page

        dialogue = ParametresEtudeDialog(
            fenetre.etude,
            parent=fenetre
        )

        # Le bloc Général existe avec titre + thème.
        assert hasattr(dialogue, "titre_etude_edit")
        assert hasattr(dialogue, "theme_combo")

        assert (
            dialogue.titre_etude_edit.text()
            == fenetre.etude.etude.titre
        )

        # Édition + enregistrement : persisté.
        dialogue.titre_etude_edit.setText(
            "Évangile selon Luc"
        )

        index = dialogue.theme_combo.findData("libre")
        dialogue.theme_combo.setCurrentIndex(index)

        dialogue.enregistrer()

        assert fenetre.etude.etude.titre == (
            "Évangile selon Luc"
        )
        assert fenetre.etude.etude.theme == "libre"

        recharge = ouvrir_etude(tmp_path / "Etude")

        assert recharge.etude.titre == "Évangile selon Luc"
        assert recharge.etude.theme == "libre"

        dialogue.close()
