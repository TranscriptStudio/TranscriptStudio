"""
Tests P18.6-bis, SÉRIE 7 — retour David du
31/10/2026 (deuxième série) :

- point 1 : fond UNIQUE #1e1f24 en thème sombre
  (le bandeau supérieur et la ligne « Dernières
  réunions » n'affichent PLUS la teinte
  #202124 de qdarktheme) ;
- point 2 : ombre de survol BEAUCOUP plus
  subtile (flou 12 px, décalée de 3 px, 4 %
  d'opacité) ;
- point 3 : plus AUCUN lien « rattacher à une
  étude… » dans la rangée d'une réunion
  autonome (le menu contextuel s'en charge) ;
- point 4 : les rangées ont toutes la MÊME
  hauteur — les steppers sont alignés ;
- point 5 : plaque des services sur UNE ligne,
  hauteur homogène avec les boutons ⚙/? ;
- point 6 : tous les SVG d'icônes au bleu
  d'accent unique #3b9eff.
"""

import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtCore import QPoint
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


def construire_accueil_mixte(tmp_path):
    """
    Hub avec DEUX réunions récentes : l'une
    RATTACHÉE à l'étude, l'autre AUTONOME
    (copie hors étude) — pour vérifier l'alignement
    des steppers et l'absence de lien.
    """

    import shutil

    from services.llm.catalogue import (
        catalogue_par_defaut,
    )
    from ui.home_window import HomeWindow

    construire_etude_test(tmp_path)

    dossier = tmp_path / "2026-10-13_Luc1b"

    copie = tmp_path / "2026-10-13_Luc1c"
    shutil.copytree(dossier, copie)

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    settings.add_recent_project(
        str(dossier / "project.sttproj")
    )

    settings.add_recent_project(
        str(copie / "project.sttproj")
    )

    settings.add_recent_etude(
        str(tmp_path / "Etude")
    )

    with patch(
        "services.llm.catalogue"
        ".charger_catalogue",
        return_value=catalogue_par_defaut(),
    ):
        accueil = HomeWindow(settings=settings)

    accueil.resize(1200, 800)
    accueil.grab()

    return accueil


#
# ==================================================
# Point 1 : fond unique en thème sombre.
# ==================================================
#

class TestFondUniqueSombre:

    def test_aucun_pixel_202124(
        self,
        qapp,
        tmp_path
    ):
        """
        qdarktheme peint tout QWidget et tout
        QLabel en #202124 — le bandeau supérieur
        et la ligne « Dernières réunions » en
        héritaient. Ces règles sont neutralisées :
        PLUS AUCUN pixel #202124 sur le hub rendu.
        """

        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.DARK
        )

        accueil = construire_accueil_mixte(tmp_path)

        try:

            image = (
                accueil
                .grab()
                .toImage()
            )

            artefact = image.pixelColor(0, 0)
            assert (
                artefact.name() == "#1e1f24"
            )

            # Balayage complet (pas de 4 px) : le
            # hub ne doit JAMAIS afficher la teinte
            # qdarktheme #202124.
            for y in range(
                0,
                image.height(),
                4
            ):
                for x in range(
                    0,
                    image.width(),
                    4
                ):
                    assert (
                        image
                        .pixelColor(x, y)
                        .name()
                        != "#202124"
                    ), (
                        f"pixel #202124 en "
                        f"({x}, {y})"
                    )

        finally:
            accueil.close()

            ThemeManager.apply_theme(
                qapp,
                ThemeManager.LIGHT
            )

            reinitialiser_theme_actif()

    def test_ligne_dernieres_reunions_au_fond(
        self,
        qapp,
        tmp_path
    ):
        """
        La bande de la ligne « Dernières réunions »
        (le label s'étire sur toute la largeur) est
        au fond de page — #1e1f24 en sombre,
        #f3f3f3 en clair, plus JAMAIS la teinte
        #202124 de qdarktheme.
        """

        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.DARK
        )

        accueil = construire_accueil_mixte(tmp_path)

        try:

            label = None

            for l in accueil.findChildren(QLabel):
                if l.text() == "Dernières réunions":
                    label = l
                    break

            assert label is not None

            origine = label.mapTo(
                accueil,
                QPoint(0, 0)
            )

            image = (
                accueil
                .grab()
                .toImage()
            )

            # Au centre vertical du label, loin du
            # texte : le fond de page, rien d'autre.
            pixel = image.pixelColor(
                accueil.width() - 40,
                origine.y() + label.height() // 2,
            )

            assert pixel.name() == "#1e1f24"

        finally:
            accueil.close()

            ThemeManager.apply_theme(
                qapp,
                ThemeManager.LIGHT
            )

            reinitialiser_theme_actif()

    def test_ligne_dernieres_reunions_clair(
        self,
        qapp,
        tmp_path
    ):
        """
        Même vérification en thème clair : la bande
        du titre est au gris Windows #f3f3f3.
        """

        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.LIGHT
        )

        accueil = construire_accueil_mixte(tmp_path)

        try:

            label = None

            for l in accueil.findChildren(QLabel):
                if l.text() == "Dernières réunions":
                    label = l
                    break

            origine = label.mapTo(
                accueil,
                QPoint(0, 0)
            )

            image = (
                accueil
                .grab()
                .toImage()
            )

            pixel = image.pixelColor(
                accueil.width() - 40,
                origine.y() + label.height() // 2,
            )

            assert pixel.name() == "#f3f3f3"

        finally:
            accueil.close()

            reinitialiser_theme_actif()


#
# ==================================================
# Point 2 : ombre de survol subtile.
# ==================================================
#

class TestOmbreSubtile:

    def test_grande_tuile(self, qapp):
        """
        Ombre des GRANDES tuiles : flou doux 12 px
        (plus 24), décalée de 3 px (plus 8), 4 %
        d'opacité (plus 8 %).
        """

        from ui.home_window import TuileAccueil

        assert (
            TuileAccueil
            .OPACITE_OMBRE_SURVOL
            == 0.04
        )
        assert (
            TuileAccueil
            .RAYON_OMBRE_SURVOL
            == 12
        )
        assert (
            TuileAccueil
            .DECALAGE_OMBRE_SURVOL
            == 3
        )

        tuile = TuileAccueil(
            "Titre",
            "Description",
        )

        try:

            assert (
                tuile._ombre.blurRadius()
                == 12
            )

            assert (
                tuile._ombre.offset()
                .y()
                == 3
            )

        finally:
            tuile.close()

    def test_tuile_reunion(self, qapp):
        """
        Ombre des tuiles-rangées (hub et page
        Étude) : mêmes canons subtils.
        """

        from ui.tuiles import (
            DECALAGE_OMBRE_SURVOL,
            OPACITE_OMBRE_SURVOL,
            RAYON_OMBRE_SURVOL,
            TuileReunion,
        )

        assert OPACITE_OMBRE_SURVOL == 0.04
        assert RAYON_OMBRE_SURVOL == 12
        assert DECALAGE_OMBRE_SURVOL == 3

        tuile = TuileReunion(
            "chemin",
            "Titre",
            "Étude « X »",
            fabrique_stepper=None,
            cout="Coût : —",
        )

        try:

            ombre = tuile.graphicsEffect()

            assert ombre is not None
            assert ombre.blurRadius() == 12
            assert ombre.offset().y() == 3

        finally:
            tuile.close()


#
# ==================================================
# Point 3 : plus de lien « rattacher à une
# étude… » dans la rangée.
# ==================================================
#

class TestPlusDeLienRattachement:

    def test_autonome_sans_lien(
        self,
        qapp,
        tmp_path
    ):
        """
        Une réunion AUTONOME n'affiche plus le lien
        « rattacher à une étude… » : le menu
        contextuel (clic droit) porte le
        rattachement ; la rangée garde la hauteur
        des autres.
        """

        from ui.home_window import HomeWindow
        from ui.tuiles import TuileReunion

        accueil = construire_accueil_mixte(tmp_path)

        try:

            libelles = [
                b.text()
                for b in (
                    accueil
                    .findChildren(QPushButton)
                )
                if b.text()
            ]

            assert (
                "rattacher à une étude…"
                not in libelles
            )

            # Le menu contextuel propose toujours
            # le rattachement d'une réunion
            # autonome.
            autonomes = [
                t for t in (
                    accueil
                    .findChildren(TuileReunion)
                )
                if t.rattachee is False
            ]

            assert len(autonomes) == 1

            menu = (
                accueil
                ._construire_menu_mini_tuile(
                    autonomes[0],
                    autonomes[0].chemin
                )
            )

            textes = [
                a.text()
                for a in menu.actions()
                if a.text()
            ]

            assert (
                "Rattacher la réunion "
                "à une étude existante"
                in textes
            )

        finally:
            accueil.close()

    def test_tuile_reunion_sans_bouton(
        self,
        qapp
    ):
        """
        La classe TuileReunion ne contient plus
        AUCUN bouton (plus de lien de
        rattachement).
        """

        from ui.tuiles import TuileReunion

        tuile = TuileReunion(
            "chemin",
            "Titre",
            None,
            fabrique_stepper=None,
            cout="Coût : —",
        )

        try:

            assert not tuile.findChildren(
                QPushButton
            )

        finally:
            tuile.close()


#
# ==================================================
# Point 4 : steppers toujours alignés.
# ==================================================
#

class TestSteppersAlignes:

    def test_hauteurs_et_steppers_alignes(
        self,
        qapp,
        tmp_path
    ):
        """
        Rattachée ou autonome, chaque rangée a la
        MÊME hauteur et son stepper est à la MÊME
        hauteur : les pastilles s'alignent en
        colonne d'une réunion à l'autre.
        """

        from ui.stepper import StepperBar
        from ui.tuiles import TuileReunion

        accueil = construire_accueil_mixte(tmp_path)

        try:

            tuiles = accueil.findChildren(
                TuileReunion
            )

            assert len(tuiles) == 2

            hauteurs = {
                t.size().height()
                for t in tuiles
            }

            assert len(hauteurs) == 1

            # Stepper de la page COURANTE de
            # chaque tuile : MÊME position relative
            # dans sa rangée et MÊME colonne (les
            # rangées sont à des ordonnées
            # différentes, c'est l'alignement
            # RELATIF qui fait la colonne).
            def stepper_courant(t):
                page = (
                    t.pile.currentWidget()
                )

                steppers = (
                    page.findChildren(
                        StepperBar
                    )
                )

                assert steppers

                return steppers[0]

            offsets = set()
            colonnes = set()

            for t in tuiles:

                origine = t.mapTo(
                    accueil,
                    QPoint(0, 0)
                )

                stepper = stepper_courant(t)

                position = stepper.mapTo(
                    accueil,
                    QPoint(0, 0)
                )

                offsets.add(
                    position.y() - origine.y()
                )

                colonnes.add(position.x())

            assert len(offsets) == 1
            assert len(colonnes) == 1

        finally:
            accueil.close()


#
# ==================================================
# Point 5 : plaque sur une ligne, hauteur
# homogène avec les boutons ⚙/?.
# ==================================================
#

class TestPlaqueUneLigne:

    def test_plaque_compacte_alignee(
        self,
        qapp,
        tmp_path
    ):
        """
        La plaque des services tient sur UNE ligne
        (les deux groupes côte à côte) et sa
        hauteur est celle des boutons ⚙/? voisins.
        """

        accueil = construire_accueil_mixte(tmp_path)

        try:

            # Les deux services sur la MÊME ligne.
            assert (
                accueil.ligne_api.y()
                == accueil.ligne_llm.y()
            )

            # Hauteur homogène avec les boutons.
            assert (
                accueil
                .plaque_services
                .height()
                == accueil
                .settings_button
                .height()
                == 34
            )

            assert (
                accueil.plaque_services.y()
                == accueil
                .settings_button
                .y()
            )

            # Info-bulles conservées (retour série 6,
            # point 2).
            assert accueil.ligne_api.toolTip()
            assert accueil.ligne_llm.toolTip()

        finally:
            accueil.close()


#
# ==================================================
# Point 6 : SVG au bleu d'accent unique.
# ==================================================
#

class TestSvgAccentUnique:

    def test_tous_les_svg_a_l_accent(self):
        """
        Tout SVG d'icône du bundle utilise le bleu
        d'accent UNIQUE #3b9eff — plus aucune
        teinte #2942ff (ni #2196f3) résiduelle.
        """

        dossier = Path(__file__).parent

        while (
            "icons" not in [
                p.name for p in dossier.iterdir()
            ]
        ):
            dossier = dossier.parent

        svgs = sorted(
            (dossier / "icons").glob("*.svg")
        )

        assert svgs

        for svg in svgs:

            contenu = svg.read_text(
                encoding="utf-8"
            )

            assert "#2942ff" not in contenu, (
                f"{svg.name} garde l'ancien bleu"
            )

            assert "#2196f3" not in contenu.lower(), (
                f"{svg.name} garde l'ancien bleu"
            )
