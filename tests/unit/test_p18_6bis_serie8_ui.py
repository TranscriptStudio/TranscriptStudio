"""
Tests P18.6-bis, SÉRIE 8 — amélioration de l'UI
transcription/correction (retour David 31/10,
points 1 à 10) et série 7 de la spec 31d
(survol des pastilles, §30, invariant 16).

- point 2 : bouton « Sauvegarder la réunion » à
  gauche de « Gestion de l'étude » ;
- point 3 : pastilles du stepper SANS numéros,
  une ICÔNE par étape ;
- point 4 : plus de bouton « Étape suivante » ;
- point 5 : thème clair — l'étape « à faire »
  est un gris très clair, jamais une forme
  noire ;
- point 7 : le texte des blocs transcrits suit
  le thème EFFECTIVEMENT appliqué (la palette Qt
  ne reflète pas qdarktheme) ;
- point 8 : l'icône A+/A− suit le thème
  effectif (le « A » invisible en clair) ;
- point 9 : l'étude/Bible est en couleur de
  police normale, alignée horizontalement avec
  la date · durée ;
- §30/invariant 16 : reflet translucide en UNE
  passe au survol des pastilles CLIQUABLES
  uniquement, teinte fonction de l'état,
  jamais en boucle ; les pastilles sans lien
  propre (hub, page Étude) restent
  entièrement statiques.
"""

import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtCore import Qt
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
    """
    Page Réunion d'une réunion rattachée à une
    étude (segmentation existante).
    """

    projet, projet_v1, etude, nom = (
        construire_etude_test(tmp_path)
    )

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    from ui.reunion_window import ReunionWindow

    fenetre = ReunionWindow(
        projet_v1,
        settings=settings,
        etude=etude,
        nom=nom
    )

    yield fenetre, projet_v1, etude, nom, settings

    fenetre.close()


#
# ==================================================
# Point 2 : bouton « Sauvegarder la réunion ».
# ==================================================
#

class TestBoutonSauvegarder:

    def test_bouton_a_gauche_de_gestion(
        self,
        reunion
    ):
        """
        « Sauvegarder » porte l'info-bulle
        « Sauvegarder la réunion » et se trouve à
        GAUCHE de « Gestion de l'étude ».
        """

        fenetre = reunion[0]

        assert (
            fenetre.sauvegarder_button.toolTip()
            == "Sauvegarder la réunion"
        )

        ruban = fenetre.gestion_button.parentWidget()

        disposition = ruban.layout()

        assert (
            disposition.indexOf(
                fenetre.sauvegarder_button
            )
            < disposition.indexOf(
                fenetre.gestion_button
            )
        )

    def test_sauvegarde_projet_et_etude(
        self,
        reunion,
        tmp_path
    ):
        """
        Sauvegarder écrit le projet v1 (drapeau
        modified retombé) puis l'étude.
        """

        fenetre, projet_v1, etude, _nom, _s = (
            reunion
        )

        chemin = projet_v1.project_file

        with patch(
            "ui.reunion_window"
            ".QMessageBox.information"
        ):
            fenetre.sauvegarder_reunion()

        from services.project_io import (
            load_project,
        )

        relu = load_project(chemin)

        assert relu.modified is False


#
# ==================================================
# Point 3 : pastilles sans numéros, avec icônes.
# ==================================================
#

class TestPastillesIcones:

    def test_libelles_et_icones(self, qapp):
        """
        Les pastilles portent le libellé SANS
        numéro et une ICÔNE non vide (micro,
        crayon, document, plateau fléché).
        """

        from ui.stepper import StepperBar

        barre = StepperBar(cliquable=True)

        try:

            libelles = [
                b.text()
                for b in barre.boutons.values()
            ]

            assert libelles == [
                "Transcription",
                "Reformulation",
                "Résumé",
                "Export",
            ]

            assert all(
                not b.icon().isNull()
                for b in barre.boutons.values()
            )

        finally:
            barre.close()


#
# ==================================================
# Points 7-8 : couleur de texte EFFECTIVE du
# thème (palette ≠ qdarktheme).
# ==================================================
#

class TestCouleurTexteEffective:

    def test_theme_applique_prime(self, qapp):
        """
        La couleur de texte suit le thème APPLIQUÉ
        (retenu par ThemeManager), pas la palette
        Qt ni le seul réglage configuré — le « A »
        des icônes A+/A− et le texte des blocs
        transcrits en dépendent.
        """

        from services.icons import (
            TEXT_COLOR_DARK_THEME,
            TEXT_COLOR_LIGHT_THEME,
            text_color_effectif,
        )
        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.LIGHT
        )

        try:
            assert text_color_effectif() == (
                TEXT_COLOR_LIGHT_THEME
            )

            ThemeManager.apply_theme(
                qapp,
                ThemeManager.DARK
            )

            assert text_color_effectif() == (
                TEXT_COLOR_DARK_THEME
            )

        finally:

            ThemeManager.apply_theme(
                qapp,
                ThemeManager.LIGHT
            )

            reinitialiser_theme_actif()

    def test_editeur_sans_boutons_doublons(
        self,
        qapp,
        tmp_path
    ):
        """
        Point 1 : l'éditeur de correction n'a plus
        les boutons 🏠 💾 📤 📖 (doublons du ruban
        de la page Réunion).
        """

        from tests.unit.test_fusion_ordre_ouvrage import (
            creer_projet_v1,
        )

        fenetre = reunion[0] if False else None

        from services.project_io import (
            load_project,
        )
        from ui.main_window import MainWindow

        projet = load_project(
            str(
                creer_projet_v1(
                    tmp_path,
                    "2026-10-13_Luc1b"
                )
                / "project.sttproj"
            )
        )

        editeur = MainWindow(
            projet,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            for attribut in (
                "home_button",
                "save_button",
                "export_button",
                "help_button",
                "reformulation_button",
            ):
                assert not hasattr(
                    editeur,
                    attribut
                )

            # La navigation de travail reste (API).
            assert hasattr(
                editeur,
                "ouvrir_reformulation"
            )

        finally:
            editeur.close()


#
# ==================================================
# Point 9 : étude/Bible alignée avec date/durée.
# ==================================================
#

class TestRuban:

    def test_badge_aligne_couleur_normale(
        self,
        reunion
    ):
        """
        L'étude « … » · Bible est sur la MÊME
        LIGNE que la date · durée (même ordonnée)
        et en couleur de police NORMALE (plus de
        bleu ni de gris atténué).
        """

        fenetre = reunion[0]

        assert (
            fenetre.badge_label.y()
            == fenetre.infos_label.y()
        )

        # Couleur normale : aucune couleur
        # personnalisée dans la feuille du badge.
        assert "color:" not in (
            fenetre.badge_label.styleSheet()
        )

        assert "color:" not in (
            fenetre.infos_label.styleSheet()
        )

        assert fenetre.badge_label.text() == (
            "Étude « Évangile de Luc » · Bible : "
            "Darby révisée"
        )


#
# ==================================================
# Série 7 (spec 31d §30, invariant 16) : reflet
# de survol des pastilles CLIQUABLES.
# ==================================================
#

class TestRefletSurvol:

    def test_teintes_par_etat(self):
        """
        §30 : fait → émeraude (46, 201, 138) ;
        en cours → blanc translucide ; à faire →
        voile clair discret — jamais un bleu
        unique imposé.
        """

        from services.avancement import (
            A_FAIRE,
            EN_COURS,
            TERMINE,
        )
        from ui.stepper import _teinte_survol

        assert _teinte_survol(TERMINE) == (
            46, 201, 138
        )

        assert _teinte_survol(EN_COURS) == (
            255, 255, 255
        )

        assert _teinte_survol(A_FAIRE) == (
            255, 255, 255
        )

    def test_reflet_une_seule_passe(
        self,
        qapp
    ):
        """
        Entrée de survol d'une pastille
        CLIQUABLE : le reflet se joue en UNE passe
        de ~900 ms (jamais en boucle), contour
        assorti, curseur main — et l'ÉTAT de la
        pastille n'est jamais modifié.
        """

        from services.theme_manager import (
            ThemeManager,
        )
        from ui.stepper import StepperBar

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.DARK
        )

        barre = StepperBar(cliquable=True)

        barre.definir_etats({
            "transcription": "termine",
        })

        try:

            bouton = barre.boutons[
                "transcription"
            ]

            assert (
                bouton.cursor().shape()
                == (
                    Qt.CursorShape
                    .PointingHandCursor
                )
            )

            etat_avant = bouton.styleSheet()

            barre._sur_entree(
                bouton,
                "transcription"
            )

            reflet = bouton._reflet

            # UNE passe, ~900 ms, jamais en boucle.
            assert reflet._animation is not None

            assert (
                reflet._animation.duration()
                == 900
            )

            assert (
                reflet._animation.loopCount()
                == 1
            )

            # L'état (fond, couleur de texte) n'est
            # pas modifié par le survol : seul le
            # CONTOUR change.
            apres = bouton.styleSheet()

            assert (
                "background-color: rgba(52,194,135,41)"
                in apres
            )

            assert "color: #45d695" in apres

            assert apres != etat_avant

        finally:
            barre.close()

    def test_sans_lien_entierement_statique(
        self,
        qapp
    ):
        """
        Invariant 16 : une pastille SANS lien
        individuel (hub, page Étude) n'affiche
        JAMAIS d'effet de survol ni de curseur
        main — pas de reflet, pas de contour.
        """

        from ui.stepper import StepperBar

        barre = StepperBar(
            cliquable=False,
            compact=True
        )

        try:

            bouton = barre.boutons[
                "transcription"
            ]

            assert not bouton.isEnabled()

            assert not hasattr(
                bouton,
                "_reflet"
            )

            assert (
                bouton.cursor().shape()
                != (
                    Qt.CursorShape
                    .PointingHandCursor
                )
            )

        finally:
            barre.close()


#
# ==================================================
# Point 5 : thème clair — pastille « à faire »
# en gris très clair (couvert aussi en série 4).
# ==================================================
#

class TestStepperClair:

    def test_a_faire_gris_tres_clair(
        self,
        qapp
    ):
        """
        En clair, l'étape non réalisée est un fond
        gris très clair (#e6e7eb, un peu plus
        soutenu que le fond de page #f3f3f3) —
        jamais une forme noire.
        """

        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )
        from ui.stepper import StepperBar

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.LIGHT
        )

        barre = StepperBar(cliquable=True)

        try:

            barre.definir_etats({
                "resume": "a_faire",
            })

            style = (
                barre.boutons["resume"]
                .styleSheet()
            )

            assert (
                "background-color: #e6e7eb" in style
            )

            assert "color: #6b6c73" in style

        finally:

            barre.close()

            ThemeManager.apply_theme(
                qapp,
                ThemeManager.LIGHT
            )

            reinitialiser_theme_actif()


#
# ==================================================
# Corrections post-série 8 (retour David 31/10) :
# icône lisible sur pastille bleue, barre
# d'outils sur la ligne du stepper, hauteur
# alignée, broadcast du changement de thème.
# ==================================================
#

class TestCorrectionsSuite:

    def test_ancre_stroke_teintee(self, qapp):
        """
        Les SVG du stepper portent la couleur sur
        stroke="#2942ff" (et non fill) : le
        teintage doit remplacer cette ancre —
        sinon l'icône restait bleu ancre sur la
        pastille bleue « en cours ».
        """

        from services.icons import (
            make_tinted_icon,
        )

        icone = make_tinted_icon(
            "#ffffff",
            "icons/stepper-transcription.svg",
            20,
            1.0
        )

        image = (
            icone.pixmap(20, 20).toImage()
        )

        couleurs = {
            image.pixelColor(x, y).name()
            for x in range(20)
            for y in range(20)
            if image.pixelColor(x, y).alpha() > 0
        }

        assert "#ffffff" in couleurs

        assert "#2942ff" not in couleurs

    def test_barre_outils_sur_la_ligne_du_stepper(
        self,
        reunion
    ):
        """
        La barre d'outils de l'éditeur (A+/A−,
        zoom, lecteur) est REPARENTÉE dans la zone
        à droite du stepper de la page Réunion,
        visible uniquement sur l'étape
        Transcription.
        """

        fenetre = reunion[0]

        fenetre.changer_etape("transcription")

        barre = (
            fenetre.fenetre_correction.barre_outils
        )

        assert (
            barre.parent() is fenetre.zone_outils
        )

        assert not fenetre.zone_outils.isHidden()

        fenetre.changer_etape("export")

        assert fenetre.zone_outils.isHidden()

    def test_hauteur_pastilles_alignee(
        self,
        qapp
    ):
        """
        Pleine taille : pastilles à 25 px
        (min-height 21 + padding + bordure), comme
        les boutons d'icônes (ICON_BUTTON_HEIGHT).
        Compact (hub, page Étude) : inchangé.
        """

        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )
        from ui.stepper import StepperBar

        ThemeManager.apply_theme(
            qapp,
            ThemeManager.DARK
        )

        barre = StepperBar(cliquable=True)
        compacte = StepperBar(
            cliquable=False,
            compact=True
        )

        try:

            barre.definir_etats({
                "export": "a_faire",
            })

            compacte.definir_etats({
                "export": "a_faire",
            })

            assert (
                "min-height: 21px"
                in barre.boutons["export"]
                .styleSheet()
            )

            assert (
                "min-height"
                not in compacte.boutons["export"]
                .styleSheet()
            )

        finally:

            barre.close()
            compacte.close()

            ThemeManager.apply_theme(
                qapp,
                ThemeManager.DARK
            )

            reinitialiser_theme_actif()

    def test_broadcast_theme_rafraichit_le_stepper(
        self,
        reunion
    ):
        """
        Changement de thème à chaud : le broadcast
        de ThemeManager recalcule les pastilles
        (elles gardaient la couleur du thème
        précédent jusqu'au survol).
        """

        from services.theme_manager import (
            ThemeManager,
            reinitialiser_theme_actif,
        )

        fenetre = reunion[0]

        #
        # Le broadcast ne rafraîchit que les
        # fenêtres VISIBLES (les fenêtres cachées
        # ne paieraient une reconstruction de
        # tuiles pour rien) : la page doit être
        # montrée.
        #
        fenetre.show()

        ThemeManager.apply_theme(
            QApplication.instance(),
            ThemeManager.DARK
        )

        styles_sombre = {
            etape: bouton.styleSheet()
            for etape, bouton in (
                fenetre.stepper.boutons.items()
            )
        }

        assert any(
            "#33343a" in style
            for style in styles_sombre.values()
        )

        ThemeManager.apply_theme(
            QApplication.instance(),
            ThemeManager.LIGHT
        )

        styles_clair = {
            etape: bouton.styleSheet()
            for etape, bouton in (
                fenetre.stepper.boutons.items()
            )
        }

        assert any(
            "#e6e7eb" in style
            for style in styles_clair.values()
        )

        assert all(
            "#33343a" not in style
            for style in styles_clair.values()
        )

        ThemeManager.apply_theme(
            QApplication.instance(),
            ThemeManager.DARK
        )

        reinitialiser_theme_actif()
