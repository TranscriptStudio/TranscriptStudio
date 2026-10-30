"""
Tests P18.6-bis, SÉRIE 2 (spec
SPEC_NAVIGATION_MODIFS_V2_2026-10-30c §18 et §20) :
plus de contour pointillé, bouton unique
« Étape suivante : [nom] › » sans « passer
l'étape › ».

Invariants complémentaires couverts : 6 et 7.
"""

import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
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


@pytest.fixture
def reunion(qapp, tmp_path):

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

    yield fenetre

    fenetre.close()


class TestSerie2:

    def test_aucun_contour_pointille(
        self,
        reunion
    ):
        """
        Invariant 6 : aucune pastille du stepper
        n'a de contour pointillé ; l'optionnalité
        ne se lit que dans le bouton « Étape
        suivante : … (optionnelle) » et
        l'info-bulle.
        """

        fenetre = reunion

        for etape, bouton in (
            fenetre.stepper.boutons.items()
        ):
            assert "dashed" not in (
                bouton.styleSheet()
            ), etape

        # Optionnalité : info-bulle des pastilles
        # ④ et ⑤ uniquement.
        assert fenetre.stepper.boutons[
            "reformulation"
        ].toolTip() == "Étape optionnelle"

        assert fenetre.stepper.boutons[
            "resume"
        ].toolTip() == "Étape optionnelle"

        # Toutes les pastilles restent navigables.
        for bouton in (
            fenetre.stepper.boutons.values()
        ):
            assert bouton.isEnabled()

    def test_action_unique_etape_suivante(
        self,
        reunion
    ):
        """
        Invariant 7 : une seule action d'avancement
        (« Étape suivante : [nom] › ») ; le saut
        d'étape se fait par clic direct sur une
        pastille.
        """

        fenetre = reunion

        boutons = [
            b.text()
            for b in (
                fenetre.findChildren(QPushButton)
            )
        ]

        # Aucun « passer l'étape ».
        assert not any(
            "passer" in b.lower()
            for b in boutons
        )

        # Une seule action d'avancement, avec le
        # nom de l'étape qui vient.
        libelle = (
            fenetre.etape_suivante_button.text()
        )

        assert libelle.startswith(
            "Étape suivante : "
        )

        assert libelle.endswith("›")
