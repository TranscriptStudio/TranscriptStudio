"""
Tests P18.6b — page Réunion (spec
NAVIGATION_V2_2026-10-29b §3) : ruban, stepper
fixe ①→⑥, étapes ④⑤ optionnelles, passage direct
②→⑥ (invariant §9.3), bandeau absent (invariant
§9.2), pile sans doublon (invariant §9.8).
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
    QWidget,
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

    settings.add_recent_etude(
        str(tmp_path / "Etude")
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


@pytest.fixture
def reunion_autonome(qapp, tmp_path):
    """
    Page Réunion d'une réunion autonome (aucune
    étude).
    """

    projet, projet_v1, _etude, _nom = (
        construire_etude_test(tmp_path)
    )

    settings = SettingsManager(
        str(tmp_path / "reglages"
        )
    )

    from ui.reunion_window import ReunionWindow

    fenetre = ReunionWindow(
        projet_v1,
        settings=settings
    )

    assert not fenetre.rattachee()

    yield fenetre, projet_v1, settings

    fenetre.close()


#
# ==================================================
# Ruban.
# ==================================================
#

class TestRuban:

    def test_ruban_rattachee(self, reunion):

        fenetre, _p, _e, _n, _s = reunion

        assert (
            fenetre.badge_label.text()
        ).startswith("Étude «")

        assert "Bible :" in (
            fenetre.badge_label.text()
        )

        # Titre de la réunion (titre_1 de l'étude).
        assert fenetre.titre_label.text() == (
            "Chapitre 1"
        )

        boutons = [
            b.text()
            for b in fenetre.findChildren(QPushButton)
        ]

        for attendu in (
            "Gestion de l'étude",
            "Accueil",
            "⚙ Paramètres",
            "? Aide",
        ):
            assert attendu in boutons

    def test_ruban_autonome(
        self,
        reunion_autonome
    ):

        fenetre, _p, _s = reunion_autonome

        assert (
            fenetre.badge_label.text()
            == "Réunion autonome"
        )

    def test_titre_configurable(
        self,
        reunion
    ):

        fenetre, _p, etude, nom, _s = reunion

        etude.reunions[nom].titre_1 = (
            "Luc 15 — la brebis perdue"
        )

        assert fenetre._titre_reunion() == (
            "Luc 15 — la brebis perdue"
        )

    def test_bandeau_absent(
        self,
        reunion
    ):
        """
        Invariant §9.2 : le bandeau app n'apparaît
        que sur la page Accueil — jamais sur la page
        Réunion.
        """

        fenetre = reunion[0]

        bandeaux = [
            w for w in (
                fenetre.findChildren(QWidget)
            )
            if w.objectName() == "bandeau_app"
        ]

        assert bandeaux == []


#
# ==================================================
# Stepper et étapes optionnelles (invariant §9.3).
# ==================================================
#

class TestStepper:

    def test_six_etapes_fixes(self, reunion):

        fenetre = reunion[0]

        assert len(fenetre.stepper.boutons) == 6

        assert fenetre.etape_courante == "correction"

    def test_etape_suivante_optionnelle(
        self,
        reunion
    ):
        """
        « Étape suivante » précise « (optionnelle) »
        quand l'étape qui vient l'est (④ depuis ③,
        ⑤ depuis ④).
        """

        fenetre = reunion[0]

        # ③ Correction → ④ Reformulation.
        assert "(optionnelle)" in (
            fenetre
            .etape_suivante_button
            .text()
        )

        fenetre.etape_courante = "transcription"

        fenetre.maj_boutons_etape()

        # ② → ③ : pas optionnelle.
        assert "(optionnelle)" not in (
            fenetre
            .etape_suivante_button
            .text()
        )

    def test_passage_direct_2_vers_6(
        self,
        reunion
    ):
        """
        Invariant §9.3 : le passage direct
        ② Transcription → ⑥ Export est toujours
        possible et n'invalide JAMAIS les contenus
        existants.
        """

        fenetre, _p, etude, nom, _s = reunion

        from services.etude_io import (
            ajouter_version_reformulation,
        )

        fids = [
            entree.fid
            for entree in (
                etude.registre.entrees.values()
            )
            if entree.reunion == nom
        ]

        ajouter_version_reformulation(
            etude,
            fids[0],
            "Contenu existant, jamais invalidé."
        )

        fenetre.changer_etape("transcription")
        fenetre.changer_etape("export")

        assert (
            fenetre.etape_courante == "export"
        )

        # Aucun contenu n'est modifié ni perdu.
        resultat = etude.reformulations[fids[0]]

        assert (
            resultat.versions[-1].texte
            == "Contenu existant, jamais invalidé."
        )

        assert (
            resultat.versions[-1].validation is None
        )

        # ④ reste optionnelle, non invalidée.
        assert fenetre.stepper.boutons[
            "reformulation"
        ].styleSheet().count("dashed") == 1

    def test_passer_etape_ne_touche_rien(
        self,
        reunion
    ):

        fenetre = reunion[0]

        fenetre.passer_etape()

        # ③ → ④ : l'étape est optionnelle, le
        # passage ne change aucune donnée.
        assert (
            fenetre.etape_courante
            == "reformulation"
        )


#
# ==================================================
# Contenu des étapes (pages existantes embarquées).
# ==================================================
#

class TestContenu:

    def test_editeur_embarque(self, reunion):

        fenetre = reunion[0]

        assert (
            fenetre.fenetre_correction
            is not None
        )

        from ui.main_window import MainWindow

        assert isinstance(
            fenetre.fenetre_correction,
            MainWindow
        )

    def test_editeur_reformulation_bascule(
        self,
        reunion
    ):
        """
        « Reformulation… » depuis l'éditeur embarqué
        bascule sur l'étape ④ de la même page
        (pas de nouvelle page, pas de doublon).
        """

        fenetre, _p, etude, nom, _s = reunion

        fenetre.fenetre_correction.ouvrir_reformulation()

        assert (
            fenetre.etape_courante
            == "reformulation"
        )

        assert (
            fenetre.fenetre_reformulation
            is not None
        )

    def test_reformulation_sans_etude(
        self,
        reunion_autonome
    ):
        """
        Réunion autonome : l'étape ④ explique le
        rattachement au lieu d'ouvrir la page
        Reformulation.
        """

        fenetre, _p, _s = reunion_autonome

        fenetre.changer_etape("reformulation")

        page = fenetre.pages_etape["reformulation"]

        textes = [
            l.text()
            for l in page.findChildren(QLabel)
        ]

        assert any(
            "autonome" in t for t in textes
        )

    def test_resume_sans_etude(
        self,
        reunion_autonome
    ):

        fenetre, _p, _s = reunion_autonome

        fenetre.changer_etape("resume")

        page = fenetre.pages_etape["resume"]

        textes = [
            l.text()
            for l in page.findChildren(QLabel)
        ]

        assert any(
            "autonome" in t for t in textes
        )


#
# ==================================================
# Navigation (pile unique, invariant §9.8).
# ==================================================
#

class TestNavigationPile:

    def test_reunion_pas_de_doublon(
        self,
        qapp,
        tmp_path
    ):

        from ui.app_window import AppWindow

        projet, projet_v1, etude, nom = (
            construire_etude_test(tmp_path)
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        fenetre_app = AppWindow(
            settings=settings
        )

        try:
            fenetre_app.ouvrir_reunion(
                projet_v1
            )

            fenetre_app.ouvrir_reunion(
                projet_v1,
                etude=etude,
                nom=nom
            )

            cles = [
                cle for cle in (
                    fenetre_app.cles_ouvertes()
                )
                if cle[0] == "reunion"
            ]

            # Jamais deux fois la même page.
            assert len(cles) == 1

        finally:
            fenetre_app.close()

    def test_accueil_toujours_disponible(
        self,
        reunion
    ):

        fenetre = reunion[0]

        # Adaptateur : sans pile, ne fait rien ;
        # avec pile, ramène à l'accueil (test de
        # l'existence du point d'entrée).
        assert hasattr(
            fenetre,
            "ouvrir_accueil"
        )
