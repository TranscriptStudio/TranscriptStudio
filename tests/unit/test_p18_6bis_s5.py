"""
Tests P18.6-bis, SÉRIE 5 — hub v4 (spec
SPEC_NAVIGATION_MODIFS_V2_2026-10-30f §25-26,
invariants 11 et 12) : plaque métal brossé,
boutons ⚙/? à une seule icône, salutation
supprimée, tuiles de réunion CLIQUABLES sans
bouton « Ouvrir », une ligne / deux lignes en
fenêtre étroite.
"""

import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
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
def hub_attache(qapp, tmp_path):

    _p, _pv, _e, _n = (
        construire_etude_test(tmp_path)
    )

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    settings.add_recent_project(
        str(
            tmp_path
            / "2026-10-13_Luc1b"
            / "project.sttproj"
        )
    )

    settings.add_recent_etude(
        str(tmp_path / "Etude")
    )

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

    yield accueil

    accueil.close()


class TestTuilesReunionV4:

    def test_pas_de_bouton_ouvrir(
        self,
        hub_attache
    ):
        """
        Invariant 11 : le hub n'affiche AUCUN
        bouton « Ouvrir » sur les tuiles de
        réunion — le clic sur la tuile ouvre la
        réunion.
        """

        accueil = hub_attache

        boutons = [
            b.text()
            for b in (
                accueil.findChildren(QPushButton)
            )
            if b.text()
        ]

        assert "Ouvrir" not in boutons

    def test_une_ligne_puis_deux_lignes(
        self,
        hub_attache
    ):
        """
        §26 : la tuile de réunion tient sur UNE
        ligne en largeur, DEUX lignes en fenêtre
        étroite, avec hauteur adaptative.
        """

        from ui.tuiles import TuileReunion

        accueil = hub_attache

        tuiles = (
            accueil.findChildren(TuileReunion)
        )

        assert tuiles

        tuile = tuiles[0]

        # Large : une ligne.
        tuile._basculer_selon_largeur(900)

        assert tuile.pile.currentWidget() is (
            tuile.page_une_ligne
        )

        # Étroit : deux lignes, hauteur adaptative
        # (plus haute).
        tuile._basculer_selon_largeur(400)

        assert tuile.pile.currentWidget() is (
            tuile.page_deux_lignes
        )

        assert (
            tuile.page_deux_lignes
            .sizeHint()
            .height()
        ) > (
            tuile.page_une_ligne
            .sizeHint()
            .height()
        )

    def test_marque_carree_accent(self, qapp):
        """
        §23/§26 : la marque carrée des tuiles de
        réunion est à l'accent #3b9eff, avec un
        halo de même teinte.
        """

        from ui.tuiles import TuileReunion

        tuile = TuileReunion(
            "chemin",
            "Titre",
            "Étude « X »",
            lien_rattachement=False,
            fabrique_stepper=None,
            cout="Coût : —",
        )

        marques = [
            l for l in (
                tuile.findChildren(QLabel)
            )
            if l.width() == 10
            and l.height() == 10
        ]

        assert marques

        style = marques[0].styleSheet()

        assert "#3b9eff" in style

        # Halo de même teinte.
        assert "rgba(59,158,255" in style

    def test_survol_anime_rangee(
        self,
        hub_attache
    ):
        """
        Invariant 10 : la tuile-rangée du hub
        passe au survol au contour #3b9eff avec
        élévation, transition ~120 ms, curseur
        main.
        """

        from PySide6.QtCore import Qt

        from ui.tuiles import TuileReunion

        accueil = hub_attache

        tuile = accueil.findChildren(
            TuileReunion
        )[0]

        assert tuile.cursor().shape() == (
            Qt.CursorShape.PointingHandCursor
        )

        assert "#3b9eff" not in (
            tuile.styleSheet()
        )

        tuile._appliquer_style(1.0)

        assert "#3b9eff" in (
            tuile.styleSheet()
        )

        tuile._appliquer_style(0.0)

        assert "#3b9eff" not in (
            tuile.styleSheet()
        )
