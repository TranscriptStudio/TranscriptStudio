"""
Tests d'invariance UI de la fenêtre Résumé (P17.1,
même outillage que la page Reformulation).

Règles testées :
- un résumé validé est figé (édition et relances
  verrouillées) ;
- la validation n'est possible que sur une version
  sauvegardée ;
- la sauvegarde d'une édition crée une nouvelle
  version edition_manuelle (jamais d'écrasement) ;
- la dévalidation rouvre l'édition.
"""

import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import QApplication

from services.etude_io import (
    ajouter_version_resume,
    devalider_version_resume,
    valider_version_resume,
)
from services.traitements.resume import (
    SOURCE_BRUTE,
)
from tests.unit.test_resume_synthese import (
    creer_etude_reunions,
)


@pytest.fixture(scope="module")
def application():

    instance = QApplication.instance()

    if instance is None:
        instance = QApplication([])

    yield instance


@pytest.fixture
def fenetre(application, tmp_path):

    from ui.resume_window import ResumeWindow

    etude, reunions = creer_etude_reunions(tmp_path)
    reunion = reunions[0]

    ajouter_version_resume(
        etude,
        reunion,
        "Premier résumé de la réunion.",
        source=SOURCE_BRUTE
    )

    fenetre = ResumeWindow(etude, reunion)
    fenetre.show()

    yield fenetre

    fenetre.close()


@pytest.mark.qt
class TestFenetreResume:

    def test_resume_non_valide_editable(self, fenetre):

        assert fenetre.resume_edit.isReadOnly() is False
        assert fenetre.valider_button.isVisible()

    def test_edition_manuelle_nouvelle_version(
        self, fenetre
    ):
        """
        La sauvegarde d'une édition crée une version
        edition_manuelle — jamais d'écrasement.
        """

        fenetre.resume_edit.setPlainText(
            "Résumé corrigé à la main."
        )

        fenetre.sauvegarder_edition()

        versions = fenetre.dernieres_versions()

        assert len(versions) == 2
        assert versions[-1].origine == (
            "edition_manuelle"
        )
        assert versions[-1].texte == (
            "Résumé corrigé à la main."
        )
        assert versions[0].texte == (
            "Premier résumé de la réunion."
        )

        assert fenetre.non_enregistre is False

    def test_validation_fige_le_resume(self, fenetre):

        fenetre.valider()

        assert fenetre.resume_edit.isReadOnly() is True

        for bouton in (
            fenetre.generer_button,
            fenetre.sauvegarder_button,
            fenetre.relancer_button,
            fenetre.selection_button,
        ):
            assert bouton.isEnabled() is False

        assert fenetre.devalider_button.isVisible()

        assert fenetre.etude.reunions[
            fenetre.reunion
        ].resume_valide is True

    def test_devalidation_rouvre_edition(
        self, fenetre
    ):

        fenetre.valider()

        assert fenetre.resume_edit.isReadOnly() is True

        fenetre.devalider()

        assert fenetre.resume_edit.isReadOnly() is False
        assert fenetre.generer_button.isEnabled()

        assert fenetre.etude.reunions[
            fenetre.reunion
        ].resume_valide is False
