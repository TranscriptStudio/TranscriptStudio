"""
Tests SÉRIE 8 navigation (SPEC_NAVIGATION_MODIFS_
V2_2026-10-31e.md §31, P18.6-bis) : fusion de
l'outillage du résumé dans la PAGE ③ Résumé du
stepper (page Réunion).

Critères :

- barre d'outils du résumé EN HAUT DE LA PAGE
  (source, longueur, ⚙ Prompts, Générer…) ;
- zone d'édition au corps de la page — la saisie
  manuelle se fait DIRECTEMENT dedans ;
- état des versions en tête de zone
  (Brouillon/Validé, détails de version) et
  indicateur au pied ;
- actions dans la page : Sauvegarder l'édition,
  Retour arrière, Relancer avec consigne…,
  Retravailler la sélection, Valider — plus de
  « Fermer » ni de fenêtre modale ;
- état vide : zone présente et prête ; source
  requise manquante = message clair À LA PLACE
  de la génération, zone restant éditable ;
- invariant complémentaire 17 : la page Résumé
  n'ouvre JAMAIS de fenêtre ou boîte de dialogue
  séparée pour éditer ou générer le résumé.
"""

import os
from pathlib import Path

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QTextEdit,
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
    étude (segmentation enregistrée).
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

    yield fenetre, projet_v1, etude, nom

    fenetre.close()


@pytest.fixture
def page_resume(qapp, tmp_path):
    """
    Page ③ Résumé d'une réunion rattachée
    (l'outillage vit dans la page).
    """

    from ui.resume_window import PageResume

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

    fenetre.changer_etape("resume")

    yield fenetre, fenetre.page_resume, etude, nom

    fenetre.close()


#
# ==================================================
# Outillage fusionné dans la page (§31).
# ==================================================
#

class TestOutillageDansLaPage:

    def test_etape_resume_embarque_la_page(
        self,
        page_resume
    ):
        """
        L'étape ③ Résumé du stepper EST la page
        Résumé : barre d'outils en haut, zone
        d'édition au corps, état des versions et
        actions dans la page.
        """

        from ui.resume_window import PageResume

        fenetre, page, _etude, _nom = (
            page_resume
        )

        assert isinstance(page, PageResume)

        # La page vit dans la pile du contenu de la
        # page Réunion (même fenêtre, jamais un
        # dialogue séparé).
        assert (
            page.window() is fenetre.window()
        )

        # Barre d'outils.
        assert page.source_combo.count() == 2
        assert (
            page.source_combo.currentText()
            == "Reformulations validées"
        )

        assert (
            page.longueur_min_spin.value()
            == 650
        )
        assert (
            page.longueur_max_spin.value()
            == 700
        )

        assert page.prompts_button.text() == (
            "⚙ Prompts"
        )

        assert page.generer_button.text() == (
            "Générer…"
        )

        # Zone d'édition : présent, ÉDITABLE (état
        # vide : prête dès l'arrivée, la saisie
        # manuelle se fait directement dedans).
        assert isinstance(
            page.resume_edit,
            QTextEdit
        )
        assert not page.resume_edit.isReadOnly()

        # État des versions en tête de zone.
        assert (
            page.version_label.text()
            == "aucune version"
        )
        assert page.statut_label.text() == (
            "Brouillon"
        )

        # Actions dans la page — pas de « Fermer »
        # ni de fenêtre modale.
        textes = [
            b.text()
            for b in page.findChildren(
                QPushButton
            )
        ]

        for attendu in (
            "Sauvegarder l'édition",
            "Retour arrière",
            "Relancer avec consigne…",
            "Retravailler la sélection",
            "Valider",
        ):
            assert attendu in textes

        assert "Fermer" not in textes

        # Le texte d'aide « fenêtre Résumé… » de
        # l'ancienne page a disparu.
        assert not hasattr(
            fenetre,
            "resume_statut_label"
        )

    def test_aucun_bouton_resume_fenetre(
        self,
        reunion
    ):
        """
        Invariant 17 (concret) : plus AUCUN bouton
        « Résumé… » dans la page Réunion, et le
        module ne référence plus de fenêtre de
        résumé.
        """

        fenetre, *_ = reunion

        for bouton in fenetre.findChildren(
            QPushButton
        ):
            assert bouton.text() != "Résumé…"

        import ui.reunion_window as module

        source = Path(
            module.__file__
        ).read_text(encoding="utf-8")

        assert "ResumeWindow" not in source
        assert "ouvrir_resume" not in source

    def test_saisie_manuelle_dans_la_page(
        self,
        page_resume
    ):
        """
        La saisie manuelle (taper/coller, sans
        appel LLM) se fait DIRECTEMENT dans la zone
        d'édition de la page, comme toute édition.
        """

        _f, page, _e, _n = page_resume

        page.resume_edit.setPlainText(
            "Résumé entièrement saisi dans la page, "
            "sans fenêtre ni appel LLM."
        )

        assert page.non_enregistre

        page.sauvegarder_edition()

        version = page.derniere_version()

        assert version is not None
        assert version.origine == (
            "edition_manuelle"
        )

    def test_source_manquante_message(
        self,
        page_resume
    ):
        """
        État vide + source requise manquante
        (aucune reformulation validée) : un MESSAGE
        CLAIR se met à la place de la génération
        (bouton « Générer… » éteint) — la zone
        d'édition RESTE prête pour la saisie
        manuelle.
        """

        _f, page, _e, _n = page_resume

        assert page.message_source

        assert not page.generer_button.isEnabled()

        assert not page.resume_edit.isReadOnly()

        # Source disponible (brute corrigée) : la
        # génération se rallume.
        page.source_combo.setCurrentIndex(1)

        assert not page.message_source

        assert page.generer_button.isEnabled()

    def test_stepper_suit_le_resume(
        self,
        page_resume
    ):
        """
        Le changement d'état du résumé (validation)
        rafraîchit le stepper de la page Réunion —
        l'étape est faite.
        """

        fenetre, page, etude, nom = (
            page_resume
        )

        page.resume_edit.setPlainText(
            "Résumé validé depuis la page."
        )

        page.sauvegarder_edition()

        page.valider()

        assert (
            etude.reunions[nom].resume_valide
            is True
        )

        # Le callback de rafraîchissement est
        # branché (maj_stepper à chaque changement).
        assert (
            page.sur_changement
            == fenetre._maj_stepper_resume
        )
