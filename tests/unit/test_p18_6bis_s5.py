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


class TestCorrectifsTechniquesS27:
    """
    Spec 30f §27 : artefact d'angle noir du menu
    déroulant Études, fonds des zones non-tuile
    identiques au fond de page #1e1f24, accueil
    ouvert en plein écran par défaut.
    """

    def test_menu_etudes_sans_artefact_coin(
        self,
        qapp,
        tmp_path
    ):
        """
        §27a : le panneau de premier niveau du menu
        Études est strictement TRANSPARENT (sans
        lui, qdarktheme repeint son fond et noircit
        les coins arrondis du conteneur).
        """

        from ui.menu_etudes import MenuEtudes

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        menu = MenuEtudes(settings)

        assert (
            "background: transparent"
            in menu.styleSheet()
        )

        # Coins arrondis du conteneur.
        assert "border-radius: 12px" in (
            menu.conteneur.styleSheet()
        )

    def test_hub_zone_dernieres_au_fond_de_page(
        self,
        qapp,
        tmp_path
    ):
        """
        §27b : le QScrollArea des dernières
        réunions (zone non-tuile) est TRANSPARENT
        — le fond affiché reste strictement le
        fond de page #1e1f24, aucune teinte
        qdarktheme intermédiaire.
        """

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )
        from ui.home_window import HomeWindow

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.DARK
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        try:

            with patch(
                "services.llm.catalogue"
                ".charger_catalogue",
                return_value=catalogue_par_defaut(),
            ):
                accueil = HomeWindow(
                    settings=settings
                )

            feuille = accueil.styleSheet()

            assert "#1e1f24" in feuille

            assert (
                "QScrollArea {"
                "background: transparent;"
                in feuille.replace("\n", "")
                or (
                    "QScrollArea" in feuille
                    and "transparent" in feuille
                )
            )

            assert (
                accueil.dernieres_scroll
                .styleSheet()
                == ""
            )

        finally:

            accueil.close()

            reinitialiser_theme_actif()

    def test_etude_liste_au_fond_de_page(
        self,
        qapp,
        tmp_path
    ):
        """
        §27b : la QListWidget des réunions de la
        page Étude est TRANSPARENTE — même fond de
        page #1e1f24 que le reste de la page.
        """

        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )
        from ui.etude_window import EtudeWindow

        construire_etude_test(tmp_path)

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.DARK
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        try:

            etude_fenetre = EtudeWindow(
                str(tmp_path / "Etude"),
                settings=settings
            )

            feuille = etude_fenetre.styleSheet()

            assert "#1e1f24" in feuille

            assert "QListWidget" in feuille

            assert "background: transparent" in (
                feuille
            )

        finally:

            etude_fenetre.close()

            reinitialiser_theme_actif()

    def test_accueil_plein_ecran_par_defaut(
        self,
    ):
        """
        §27c : le point d'entrée ouvre l'accueil
        en PLEIN ÉCRAN (showMaximized), plus une
        fenêtre 550x500.
        """

        from pathlib import Path

        source = Path(
            __file__
        ).parents[2].joinpath(
            "TranscriptStudio.py"
        ).read_text(
            encoding="utf-8"
        )

        assert "showMaximized()" in source

        assert "window.show()" not in source
