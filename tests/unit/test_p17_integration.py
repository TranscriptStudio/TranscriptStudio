"""
Tests d'intégration P17 (bloc Résumé + synthèse
d'étude + récurrences) APRÈS la refonte P16-bis
(page Reformulation réécrite, assurer_decoupage
partagé, navigation à pile unique).

P17 est livré (commits 51af999, 725e9c9, 14d1c27) ;
ces fumées vérifient que son câblage UI tient :

- chaque validation de bloc appelle le déclencheur
  de la synthèse d'étude (P17.2, validation_bloc,
  contrat §9) et la condition « réunion
  entièrement validée » du service devient vraie
  au dernier bloc ;
- « Résumé… » depuis la page Étude : segmentation
  assurée par la fonction partagée, fenêtre
  Résumé ouverte pour la bonne réunion (P17.1) ;
- « Récurrences… » : le rapport s'affiche sans
  erreur (P17.3).
"""

import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import QApplication

from services.etude_io import (
    ajouter_version_reformulation,
    ouvrir_etude,
    valider_version_reformulation,
)
from services.settings import SettingsManager
from services.traitements.synthese import (
    reunion_entierement_validee,
)
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
def fenetre_reformulation(qapp, tmp_path):
    """
    Page Reformulation d'une réunion de 3 blocs,
    réglages isolés.
    """

    _projet, _projet_v1, _etude, nom = (
        construire_etude_test(tmp_path)
    )

    etude_disco = ouvrir_etude(tmp_path / "Etude")

    from ui.reformulation_window import (
        ReformulationWindow
    )

    fenetre = ReformulationWindow(
        etude_disco,
        nom,
        settings=SettingsManager(
            str(tmp_path / "reglages")
        )
    )

    yield fenetre

    fenetre.close()


@pytest.fixture
def page_etude(qapp, tmp_path):

    _projet, _projet_v1, _etude, nom = (
        construire_etude_test(tmp_path)
    )

    from ui.etude_window import EtudeWindow

    page = EtudeWindow(
        tmp_path / "Etude",
        settings=SettingsManager(
            str(tmp_path / "reglages")
        )
    )

    yield page, nom

    page.close()


@pytest.mark.qt
class TestP17Integration:

    def test_validation_complete_declenche_la_synthese(
        self,
        fenetre_reformulation
    ):
        """
        P17.2 : chaque validation de bloc appelle le
        déclencheur de mise à jour de la synthèse
        (le hook interne décide) ; la condition
        « réunion entièrement validée » du service
        ne devient vraie qu'au dernier bloc validé.
        """

        for fid in (1, 2, 3):
            ajouter_version_reformulation(
                fenetre_reformulation.etude,
                fid,
                f"Reformulation validée du bloc {fid}.",
                type_version="passe",
            )

            fenetre_reformulation.rafraichir_ligne(fid)

        etude = fenetre_reformulation.etude
        reunion = fenetre_reformulation.reunion

        with patch.object(
            fenetre_reformulation,
            "maj_synthese_si_reunion_validee"
        ) as declencheur:

            # Réunion incomplète : la condition du
            # service est fausse.
            fenetre_reformulation.valider_bloc(1)

            assert declencheur.called

            assert not reunion_entierement_validee(
                etude,
                reunion
            )

            fenetre_reformulation.valider_bloc(2)

            assert not reunion_entierement_validee(
                etude,
                reunion
            )

            # Le dernier bloc complète la réunion :
            # la condition devient vraie — le
            # déclencheur (mocké ici) lancerait la
            # génération.
            fenetre_reformulation.valider_bloc(3)

            assert declencheur.call_count == 3

        assert reunion_entierement_validee(
            etude,
            reunion
        )

        assert fenetre_reformulation.etat_bloc(3) == (
            "validee"
        )

    def test_resume_depuis_la_page_etude(
        self,
        page_etude
    ):
        """
        P17.1 : « Résumé… » ouvre la fenêtre Résumé
        de la réunion sélectionnée — la segmentation
        (déjà enregistrée) est assurée par la
        fonction partagée, sans dialogue.
        """

        page, nom = page_etude

        # Sélection de la réunion dans la liste.
        assert page.reunions_liste.count() >= 1

        page.reunions_liste.setCurrentRow(0)

        assert page.reunion_selectionnee() == nom

        with patch(
            "ui.resume_window.ResumeWindow"
        ) as fenetre_resume:

            with patch.object(
                page,
                "_assurer_decoupage",
                wraps=page._assurer_decoupage
            ) as assurer:

                page.ouvrir_reunion_resume()

            # Segmentation existante : assurée sans
            # confirmation, pour LA réunion choisie.
            assert assurer.called

            assert (
                assurer.call_args[0][0] == nom
            )

            # La fenêtre Résumé est ouverte pour la
            # bonne réunion de la bonne étude, et le
            # dialogue est exécuté (mocké en test).
            assert fenetre_resume.called

            args = fenetre_resume.call_args

            assert args[0][0] is page.etude
            assert args[0][1] == nom

            assert (
                fenetre_resume.return_value.exec.called
            )

    def test_recurrences_depuis_la_page_etude(
        self,
        page_etude
    ):
        """
        P17.3 : « Récurrences… » produit le rapport
        (message propre quand aucune expression
        n'est signalée — une seule réunion dans
        l'étude de test).
        """

        page, nom = page_etude

        with patch(
            "ui.etude_window.QMessageBox.information"
        ) as information:

            page.afficher_recurrences()

            assert information.called
