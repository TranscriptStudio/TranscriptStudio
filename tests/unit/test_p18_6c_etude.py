"""
Tests P18.6c — page Étude refondue (spec
NAVIGATION_V2_2026-10-29b §4) : ruban, liste des
réunions en une colonne (avancement ①→⑤ SANS ⑥ —
invariant §9.4), réordonnancement (ordre
d'ouvrage), « Ajouter une réunion », synthèse
(« régénérer » / « éditer »), renvoi export
ouvrage vers la page Ouvrage.
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

from services.etude_io import ouvrir_etude
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
def page(qapp, tmp_path):

    _p, _pv, _e, _nom = construire_etude_test(
        tmp_path
    )

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    settings.add_recent_etude(
        str(tmp_path / "Etude")
    )

    from ui.etude_window import EtudeWindow

    fenetre = EtudeWindow(
        tmp_path / "Etude",
        settings=settings
    )

    yield fenetre, tmp_path, settings

    fenetre.close()


#
# ==================================================
# Ruban.
# ==================================================
#

class TestRuban:

    def test_ruban(self, page):

        fenetre, tmp_path, _s = page

        assert fenetre.ruban.objectName() == (
            "ruban_etude"
        )

        assert fenetre.titre_label.text() == (
            "Évangile de Luc"
        )

        # Thème + nombre de réunions (pluriel
        # propre, spec correctifs §15).
        assert "1 réunion" in (
            fenetre.sous_titre_label.text()
        )

        assert "réunion(s)" not in (
            fenetre.sous_titre_label.text()
        )

        # Badge Bible · versification.
        assert fenetre.badge_bible_label \
            .text().startswith("Bible :")

        assert "versification :" in (
            fenetre.badge_bible_label.text()
        )

        boutons = [
            b.text()
            for b in fenetre.findChildren(QPushButton)
        ]

        for attendu in (
            "Modifier l'étude",
            "Accueil",
            "⚙ Paramètres",
            "? Aide",
        ):
            assert attendu in boutons

    def test_bandeau_absent(self, page):
        """
        Invariant §9.2 : le bandeau app n'apparaît
        que sur la page Accueil.
        """

        fenetre = page[0]

        bandeaux = [
            w for w in (
                fenetre.findChildren(QWidget)
            )
            if w.objectName() == "bandeau_app"
        ]

        assert bandeaux == []

    def test_modifier_etude(self, page):

        fenetre, tmp_path, _s = page

        class DialogueFictif:

            def __init__(self, titre, theme, parent):
                pass

            def exec(self):
                return True

            def resultat(self):
                return (
                    "Évangile selon Luc",
                    "libre"
                )

        with patch(
            "ui.modifier_etude_dialog"
            ".ModifierEtudeDialog",
            DialogueFictif
        ):
            fenetre.modifier_etude()

        assert fenetre.etude.etude.titre == (
            "Évangile selon Luc"
        )

        assert fenetre.etude.etude.theme == "libre"

        assert fenetre.titre_label.text() == (
            "Évangile selon Luc"
        )

        # Persisté.
        recharge = ouvrir_etude(tmp_path / "Etude")

        assert recharge.etude.titre == (
            "Évangile selon Luc"
        )


#
# ==================================================
# Liste des réunions : mini-tuiles, avancement
# ①→⑤ sans ⑥ (invariant §9.4).
# ==================================================
#

class TestListeReunions:

    def test_avancement_sans_export(self, page):
        """
        Invariant §9.4 : l'affichage d'avancement
        d'une réunion sur la page Étude ne montre
        JAMAIS l'étape ⑥ Export.
        """

        fenetre = page[0]

        assert fenetre.reunions_liste.count() == 1

        from ui.stepper import StepperBar

        steppers = (
            fenetre.findChildren(StepperBar)
        )

        assert steppers

        for stepper in steppers:

            libelles = [
                b.text()
                for b in stepper.boutons.values()
            ]

            assert "④ Export" not in libelles

            # Page Étude : Transcription →
            # Reformulation → Résumé (3 pastilles,
            # P18.6-bis §19).
            assert len(libelles) == 3

    def test_mini_tuile_infos(self, page):

        fenetre = page[0]

        from ui.stepper import StepperBar

        steppers = (
            fenetre.findChildren(StepperBar)
        )

        assert steppers

        boutons = [
            b.text()
            for b in (
                fenetre.findChildren(QPushButton)
            )
        ]

        assert "Ouvrir" in boutons

        # Boutons par tuile supprimés (spec
        # correctifs §14) : seul « Ouvrir » reste,
        # avec la poignée de réordonnancement.
        assert "Reformulation…" not in boutons
        assert "Résumé…" not in boutons

        # Poignée de réordonnancement.
        assert "↑" in boutons
        assert "↓" in boutons

        # Coût affiché par réunion.
        couts = [
            l.text()
            for l in fenetre.findChildren(QLabel)
            if l.text().startswith("Coût :")
        ]

        assert couts

    def test_reordonnancement(self, tmp_path):
        """
        L'ordre vaut ordre d'ouvrage : la poignée
        réordonne les réunions de l'étude.
        """

        _p, _pv, _e, _n = construire_etude_test(
            tmp_path
        )

        etude = ouvrir_etude(tmp_path / "Etude")

        from services.etude_io import (
            ajouter_reunion,
        )

        # Une seconde réunion (copie du projet v1).
        import shutil

        dossier2 = tmp_path / "Autre_reunion"

        shutil.copytree(
            tmp_path / "2026-10-13_Luc1b",
            dossier2
        )

        nom2 = ajouter_reunion(
            etude,
            dossier2,
            titre_1="Chapitre 2"
        )

        from services.etude_io import (
            sauvegarder_etude,
        )

        sauvegarder_etude(etude)

        from ui.etude_window import EtudeWindow

        fenetre = EtudeWindow(
            tmp_path / "Etude",
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            nom1 = (
                etude.etude.ordre_reunions[0]
            )

            fenetre._deplacer_reunion(nom2, -1)

            assert fenetre.etude \
                .etude.ordre_reunions == [
                    nom2,
                    nom1,
                ]

            # Persisté : l'ordre d'ouvrage est
            # enregistré.
            recharge = ouvrir_etude(
                tmp_path / "Etude"
            )

            assert recharge \
                .etude.ordre_reunions == [
                    nom2,
                    nom1,
                ]

        finally:
            fenetre.close()


#
# ==================================================
# Synthèse : « régénérer » / « éditer ».
# ==================================================
#

class TestSynthese:

    def test_editer_manuellement(self, page):

        fenetre, tmp_path, _s = page

        # Lecture seule par défaut.
        assert fenetre.synthese_edit.isReadOnly()

        fenetre.editer_synthese()

        assert not (
            fenetre.synthese_edit.isReadOnly()
        )

        assert fenetre.synthese_sauver_button \
            .isVisibleTo(fenetre)

        fenetre.synthese_edit.setPlainText(
            "Synthèse saisie à la main."
        )

        fenetre.sauvegarder_edition_synthese()

        # Nouvelle version « manuel », retour en
        # lecture seule.
        assert fenetre.synthese_edit.isReadOnly()

        versions = (
            fenetre.etude.synthese.versions
        )

        assert versions

        assert versions[-1].texte == (
            "Synthèse saisie à la main."
        )

        assert (
            versions[-1].declencheur == "manuel"
        )


#
# ==================================================
# Renvoi export ouvrage vers la page Ouvrage.
# ==================================================
#

class TestRenvoiOuvrage:

    def test_bouton_ouvrage(self, page):

        fenetre = page[0]

        assert fenetre.ouvrage_button.text() == (
            "Ouvrage…"
        )

    def test_renvoi_pile(self, qapp, tmp_path):
        """
        La page Ouvrage s'ouvre depuis la page
        Étude via la pile unique — jamais deux fois
        la même page (invariant §9.8).
        """

        from ui.app_window import AppWindow

        _p, _pv, _e, _n = (
            construire_etude_test(tmp_path)
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.add_recent_etude(
            str(tmp_path / "Etude")
        )

        fenetre_app = AppWindow(settings=settings)

        try:

            etude = ouvrir_etude(tmp_path / "Etude")

            fenetre_app.ouvrir_ouvrage(etude)
            fenetre_app.ouvrir_ouvrage(etude)

            cles = [
                cle for cle in (
                    fenetre_app.cles_ouvertes()
                )
                if cle[0] == "ouvrage"
            ]

            assert len(cles) == 1

            from ui.ouvrage_window import (
                OuvrageWindow
            )

            page_ouvrage = (
                fenetre_app.page_active()
            )

            assert isinstance(
                page_ouvrage,
                OuvrageWindow
            )

            assert (
                page_ouvrage
                .exporter_button.text()
                .strip()
                == "📤 Exporter l'ouvrage…"
            )

        finally:
            fenetre_app.close()

    def test_ouvrir_reunion_depuis_etude(
        self,
        qapp,
        tmp_path
    ):
        """
        « Ouvrir » d'une mini-tuile : la page
        Réunion s'ouvre via la pile, avec l'étude
        et le nom de la réunion.
        """

        from ui.app_window import AppWindow

        _p, _pv, _e, nom = (
            construire_etude_test(tmp_path)
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.add_recent_etude(
            str(tmp_path / "Etude")
        )

        fenetre_app = AppWindow(settings=settings)

        try:

            fenetre_app.ouvrir_etude(
                tmp_path / "Etude"
            )

            page_etude = (
                fenetre_app.page_active()
            )

            page_etude._ouvrir_reunion(nom)

            from ui.reunion_window import (
                ReunionWindow
            )

            assert isinstance(
                fenetre_app.page_active(),
                ReunionWindow
            )

            reunion = (
                fenetre_app.page_active()
            )

            assert reunion.nom == nom

            assert reunion.rattachee()

        finally:
            fenetre_app.close()
