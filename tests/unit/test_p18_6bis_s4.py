"""
Tests P18.6-bis, SÉRIE 4 (spec
SPEC_NAVIGATION_MODIFS_V2_2026-10-30e §21-22) :
tuile « Études » = menu déroulant atterrissant
directement sur la page Étude (jamais de page
intermédiaire — invariant 1 réécrit), tuiles en
conformité avec les maquettes : CONTOURS
VISIBLES sur toutes les tuiles, effet de survol
(élévation ~2 px, contour au bleu d'accent
#4a7db5, transition ~120 ms, retour immédiat,
curseur main), 3 grandes cartes en 3 colonnes.
"""

import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtCore import QEvent, QPointF
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
)


def evenement_entree() -> QEnterEvent:
    return QEnterEvent(
        QPointF(1, 1),
        QPointF(1, 1),
        QPointF(1, 1),
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
def hub(qapp, tmp_path):

    from services.llm.catalogue import (
        catalogue_par_defaut,
    )
    from ui.home_window import HomeWindow

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    with patch(
        "services.llm.catalogue.charger_catalogue",
        return_value=catalogue_par_defaut(),
    ):
        accueil = HomeWindow(settings=settings)

    yield accueil

    accueil.close()


#
# ==================================================
# Couleurs des maquettes (§22) — contours visibles.
# ==================================================
#

class TestCouleursTuiles:

    def test_couleurs_maquettes(self):
        """
        Thème sombre : couleurs EXACTES des
        maquettes (fond de tuile #2a2b31, bord
        1 px #3a3b42, fond de page #1e1f24) ; bleu
        d'accent #4a7db5 au survol.
        """

        from services.theme_manager import (
            BORD_BLEU_ACCENT,
            FOND_PAGE_SOMBRE,
            couleurs_tuiles,
        )

        assert BORD_BLEU_ACCENT == "#4a7db5"
        assert FOND_PAGE_SOMBRE == "#1e1f24"

        sombre = couleurs_tuiles(True)

        assert sombre["fond"] == "#2a2b31"
        assert sombre["bord"] == "#3a3b42"
        assert sombre["fond_survol"]

        # Thème clair : contour également visible
        # (gris net sur fond de page clair).
        clair = couleurs_tuiles(False)

        assert clair["bord"] not in (
            "",
            sombre["fond"],
        )


#
# ==================================================
# Grandes cartes du hub (§22) : contour, survol,
# trois colonnes.
# ==================================================
#

class TestCartesHub:

    def test_contour_visible_et_survol(self, hub):

        accueil = hub

        style = (
            accueil.tuile_nouvelle.styleSheet()
        )

        # CONTOUR VISIBLE : bordure 1 px nette.
        assert "border: 1px solid" in style

        assert "border-radius" in style

        # Fond de tuile distinct (la tuile se
        # détache du fond, jamais ne s'y fond).
        assert "background-color" in style

        # SURVOL : contour au bleu d'accent.
        assert ":hover" in style

        assert "#4a7db5" in style

    def test_curseur_main(self, hub):

        accueil = hub

        from PySide6.QtCore import Qt

        for tuile in (
            accueil.tuile_nouvelle,
            accueil.tuile_reprendre,
            accueil.tuile_etudes,
        ):
            assert tuile.cursor().shape() == (
                Qt.CursorShape.PointingHandCursor
            )

    def test_trois_colonnes_egales(self, hub):
        """
        §22 : 3 grandes cartes en 3 COLONNES —
        stretch identique, pas de colonne résiduelle.
        """

        accueil = hub

        layout = accueil.tuiles_layout

        assert layout.count() == 3

        for index in range(3):
            assert layout.stretch(index) == 1

    def test_elevation_au_survol(self, hub):
        """
        §22 : élévation ~2 px animée (~120 ms) à
        l'entrée, retour IMMÉDIAT en sortie.
        """

        accueil = hub

        tuile = accueil.tuile_nouvelle

        assert tuile.ELEVATION_SURVOL == 2
        assert tuile.DUREE_SURVOL_MS == 120

        base = tuile.pos()

        tuile.enterEvent(evenement_entree())

        # Animation lancée, durée ~120 ms.
        assert tuile._animation is not None
        assert tuile._animation.duration() == 120

        # Sortie de survol : retour immédiat.
        tuile.leaveEvent(
            QEvent(QEvent.Type.Leave)
        )

        assert tuile._animation is None
        assert tuile.pos() == base


#
# ==================================================
# Tuiles-rangées de la page Étude (§22) : contour
# visible + survol, un seul bouton Ouvrir et le
# coût.
# ==================================================
#

class TestTuilesEtude:

    def test_contour_et_survol(self, qapp, tmp_path):

        _p, _pv, _e, _n = (
            construire_etude_test(tmp_path)
        )

        from ui.etude_window import EtudeWindow

        page = EtudeWindow(
            tmp_path / "Etude",
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            tuiles = [
                w for w in (
                    page.reunions_liste
                    .findChildren(QFrame)
                )
                if w.objectName()
                == "etude_mini_tuile"
            ]

            assert tuiles

            style = tuiles[0].styleSheet()

            assert "border: 1px solid" in style
            assert "background-color" in style

            # Survol : contour au bleu d'accent.
            assert ":hover" in style
            assert "#4a7db5" in style

            # Curseur main (cliquable).
            from PySide6.QtCore import Qt

            assert tuiles[0].cursor().shape() == (
                Qt.CursorShape.PointingHandCursor
            )

        finally:
            page.close()

    def test_bouton_unique_ouvrir(self, qapp, tmp_path):
        """
        §22 : tuiles-rangées sobres — un seul
        bouton « Ouvrir » (avec la poignée de
        réordonnancement préservée, sans régression
        ⠿) et le coût ; pas de boutons empilés.
        """

        _p, _pv, _e, _n = (
            construire_etude_test(tmp_path)
        )

        from ui.etude_window import EtudeWindow

        page = EtudeWindow(
            tmp_path / "Etude",
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            tuiles = [
                w for w in (
                    page.reunions_liste
                    .findChildren(QFrame)
                )
                if w.objectName()
                == "etude_mini_tuile"
            ]

            assert tuiles

            from PySide6.QtWidgets import (
                QPushButton,
            )

            boutons = [
                b.text()
                for b in (
                    tuiles[0]
                    .findChildren(QPushButton)
                )
            ]

            assert boutons.count("Ouvrir") == 1

            # Poignée de réordonnancement préservée
            # (livraison : aucune régression ⠿).
            assert "↑" in boutons
            assert "↓" in boutons

            # Pas de boutons empilés par tuile.
            assert (
                "Reformulation…" not in boutons
            )
            assert "Résumé…" not in boutons

        finally:
            page.close()


#
# ==================================================
# Conformité à la maquette (icônes, lignes du
# menu, date française, pastille stable).
# ==================================================
#

class TestMaquette:

    def test_icones_des_tuiles(self, hub):
        """
        Maquette : chaque grande carte porte SON
        icône SVG (micro, dossier, livre ouvert),
        teinte bleu d'accent — plus de tuile sans
        icône.
        """

        accueil = hub

        for tuile in (
            accueil.tuile_nouvelle,
            accueil.tuile_reprendre,
            accueil.tuile_etudes,
        ):
            pixmaps = [
                l for l in (
                    tuile.findChildren(QLabel)
                )
                if not l.pixmap().isNull()
            ]

            assert pixmaps, (
                "la tuile « "
                + tuile.titre
                + " » doit porter une icône"
            )

    def test_date_francaise(self):
        """
        « modifiée le 27 oct. 2026 » à partir du
        champ modification d'etude.json.
        """

        from ui.menu_etudes import (
            formater_date_modification,
        )

        assert formater_date_modification(
            "2026-10-27T21:12:51"
        ) == "modifiée le 27 oct. 2026"

        assert formater_date_modification(
            "2026-01-05T08:00:00"
        ) == "modifiée le 5 janv. 2026"

        assert formater_date_modification("") == ""
        assert (
            formater_date_modification("pas une date")
            == ""
        )

    def test_pastille_stable(self):
        """
        La pastille d'une étude garde la même
        couleur d'un affichage à l'autre
        (déterminée par le dossier).
        """

        from ui.menu_etudes import (
            PALETTE_PASTILLES,
            couleur_pastille,
        )

        dossier = "C:/etudes/Evangile"

        assert couleur_pastille(dossier) == (
            couleur_pastille(dossier)
        )

        assert (
            couleur_pastille(dossier)
            in PALETTE_PASTILLES
        )

        # Des études différentes peuvent différer.
        assert len({
            couleur_pastille("etude-a"),
            couleur_pastille("etude-b"),
            couleur_pastille("etude-c"),
        }) > 1

    def test_lire_etude_legere(self, tmp_path):
        """
        Lecture légère des métadonnées (titre,
        thème, modification) sans charger l'étude.
        """

        _p, _pv, _e, _n = (
            construire_etude_test(tmp_path)
        )

        from services.rattachement import (
            lire_etude_legere,
        )

        infos = lire_etude_legere(
            tmp_path / "Etude"
        )

        assert infos["titre"] == (
            "Évangile de Luc"
        )

        assert infos["theme"] == "livre"

        assert infos["modification"]

        assert lire_etude_legere(
            tmp_path / "inexistant"
        ) is None

    def test_couleurs_menu_maquette(self):
        """
        Couleurs exactes du panneau (thème sombre,
        maquette) : fond #26272d, bord #3d4152.
        """

        from services.theme_manager import (
            couleurs_menu_etudes,
        )

        sombre = couleurs_menu_etudes(True)

        assert sombre["fond"] == "#26272d"
        assert sombre["bord"] == "#3d4152"
        assert sombre["survol_item"] == "#2c2d33"

        clair = couleurs_menu_etudes(False)

        assert clair["fond"] != sombre["fond"]
