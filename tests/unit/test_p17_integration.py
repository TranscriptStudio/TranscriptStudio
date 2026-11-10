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

    def test_validation_complete_ne_declenche_plus_la_synthese(
        self,
        fenetre_reformulation
    ):
        """
        P20.6 (abrogation de P17.2, invariant 8) :
        AUCUNE écriture automatique de la synthèse à
        la validation d'une réunion — même quand la
        réunion devient entièrement validée.
        """

        for fid in (1, 2, 3):
            ajouter_version_reformulation(
                fenetre_reformulation.etude,
                fenetre_reformulation.reunion,
                fid,
                f"Reformulation validée du bloc {fid}.",
                type_version="passe",
            )

            fenetre_reformulation.rafraichir_ligne(fid)

        etude = fenetre_reformulation.etude
        reunion = fenetre_reformulation.reunion

        assert not etude.synthese.versions

        fenetre_reformulation.valider_bloc(1)
        fenetre_reformulation.valider_bloc(2)
        fenetre_reformulation.valider_bloc(3)

        # Réunion entièrement validée…
        assert reunion_entierement_validee(
            etude,
            reunion
        )

        # …mais AUCUNE synthèse écrite (invariant 8).
        assert not etude.synthese.versions

        assert fenetre_reformulation.etat_bloc(3) == (
            "validee"
        )

    def test_resume_depuis_la_page_etude(
        self,
        page_etude
    ):
        """
        Série 8 (SPEC_NAVIGATION_MODIFS 31e §31) :
        « Résumé » mène à la PAGE Réunion, étape ⑤
        Résumé — tout l'outillage vit dans la page,
        la fenêtre secondaire « Résumé… » est
        supprimée de l'app (invariant complémentaire
        17). La segmentation (déjà enregistrée) est
        assurée par la fonction partagée, sans
        dialogue.
        """

        page, nom = page_etude

        # Sélection de la réunion dans la liste.
        assert page.reunions_liste.count() >= 1

        page.reunions_liste.setCurrentRow(0)

        assert page.reunion_selectionnee() == nom

        ouvertures = []

        class NavigationFactice:

            def ouvrir_reunion(
                self,
                projet,
                etude=None,
                nom=None,
                etape=None
            ):
                ouvertures.append({
                    "etude": etude,
                    "nom": nom,
                    "etape": etape,
                })

        page.navigation = NavigationFactice()

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

        # La page Réunion est ouverte à l'étape
        # Résumé de la bonne réunion de la bonne
        # étude — jamais une fenêtre séparée.
        assert len(ouvertures) == 1

        assert ouvertures[0]["etude"] is page.etude

        assert ouvertures[0]["nom"] == nom

        assert ouvertures[0]["etape"] == "resume"

    def test_plus_de_recurrences_sur_la_page_etude(
        self,
        page_etude
    ):
        """
        Amendement 2026-11-09 (P20.3) : l'aide à
        l'écriture globale vit UNIQUEMENT sur la page
        Ouvrage — plus aucun point d'entrée « Récurrences »
        sur la page Étude.
        """

        page, nom = page_etude

        assert not hasattr(page, "afficher_recurrences")
