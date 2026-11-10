"""
Tests P19.2/P19.3 — page Ouvrage à trois zones
(arborescence à la Word, manuscrit compilé
éditable, rapport), branchée sur le document
dérivé P19.1 (feuille de route v2.1 §P19,
maquette validée 2026-10-29).

Critères de la feuille de route :

- ouvrage généré pour une étude de 2+ blocs
  validés (ordre d'ouvrage, provenances) ;
- structure lisible indépendamment des
  réunions : chapitres manuels, paragraphes
  placés dessous, « Réserves » sinon ;
- provenance consultable par paragraphe ;
- navigation par structure (clic arbre →
  manuscrit) ;
- régénération complète qui ÉCRASE
  (avertissement) ;
- signalement « réunion re-reformulée depuis
  la génération » ;
- sauvegarde dans l'étude (ouvrage.json).
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
    QLineEdit,
    QMessageBox,
    QTextEdit,
)

from models.ouvrage import (
    TYPE_TITRE_1,
)
from services.etude_io import (
    ajouter_version_reformulation,
    valider_version_reformulation,
)
from services.ouvrage_document import (
    charger_ouvrage,
    chemin_ouvrage,
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
def etude_validee(qapp, tmp_path):
    """
    Étude d'une réunion de TROIS blocs, tous avec
    une reformulation VALIDÉE.
    """

    _p, _pv, etude, nom = (
        construire_etude_test(tmp_path)
    )

    fids = [
        entree.fid
        for entree in (
            etude.registre.entrees.values()
        )
        if entree.reunion == nom
    ]

    for fid in fids:

        version = ajouter_version_reformulation(
            etude,
            nom,
            fid,
            f"Reformulation du bloc {fid}"
        )

        valider_version_reformulation(
            etude,
            nom,
            fid,
            version.numero,
            "Test"
        )

    return etude, nom, fids, tmp_path


@pytest.fixture
def page(qapp, etude_validee):

    etude, _nom, _fids, tmp_path = (
        etude_validee
    )

    from ui.ouvrage_window import OuvrageWindow

    fenetre = OuvrageWindow(
        etude,
        settings=SettingsManager(
            str(tmp_path / "reglages")
        )
    )

    yield fenetre

    fenetre.close()


#
# ==================================================
# État initial et génération (P19.3).
# ==================================================
#

class TestGenerationPage:

    def test_sans_document(
        self,
        page
    ):
        """
        Sans ouvrage généré : rapport « Aucun
        ouvrage généré », bouton « Générer »,
        outils de structure désactivés.
        """

        assert page.document is None

        assert (
            page.generer_button.text()
            == "⚡ Générer l'ouvrage"
        )

        assert not page.chapitre_button.isEnabled()

        assert "Aucun ouvrage généré" in (
            page.rapport_zone.toPlainText()
        )

    def test_generation(
        self,
        page,
        etude_validee
    ):
        """
        Générer initialise le document depuis les
        reformulations validées (3 paragraphes),
        l'écrit dans l'étude, remplit les trois
        zones — tout est en « Réserves » (aucun
        chapitre manuel).
        """

        _e, _n, _f, tmp_path = etude_validee

        page.generer_ouvrage()

        assert page.document is not None

        assert chemin_ouvrage(
            tmp_path / "Etude"
        ).is_file()

        # Manuscrit : un éditeur par élément
        # (3 paragraphes), provenance visible.
        paragraphes = page.document.paragraphes()

        assert len(paragraphes) == 3

        assert len(page.editeurs) == 3

        editeur = page.editeurs[
            paragraphes[0].id
        ]

        assert isinstance(
            editeur.findChild(QTextEdit),
            QTextEdit
        )

        # Arborescence : un nœud « Réserves »
        # avec les trois paragraphes.
        libelles = [
            page.arbre.topLevelItem(i).text(0)
            for i in range(
                page.arbre.topLevelItemCount()
            )
        ]

        assert libelles == ["Réserves"]

        reserves = page.arbre.topLevelItem(0)

        assert reserves.childCount() == 3

        # Rapport : état de la génération.
        rapport = (
            page.rapport_zone.toPlainText()
        )

        assert "Ouvrage généré le" in rapport
        assert "3 paragraphe(s)" in rapport

        assert (
            page.generer_button.text()
            == "⟳ Régénérer…"
        )

        assert page.chapitre_button.isEnabled()

    def test_regenerer_ecrase_avec_avertissement(
        self,
        page
    ):
        """
        La régénération complète ÉCRASE — mais
        UNIQUEMENT après l'avertissement explicite
        (« Non » ne touche à rien).
        """

        page.generer_ouvrage()

        page._ajouter_element(
            TYPE_TITRE_1,
            "Chapitre manuel"
        )

        chapitre_id = page.editeurs[
            page.document.elements[0].id
        ]

        assert chapitre_id is not None

        # « Non » : le document est préservé.
        with patch(
            "ui.ouvrage_window"
            ".QMessageBox.warning",
            return_value=(
                QMessageBox.StandardButton.No
            )
        ):
            page.generer_ouvrage()

        assert page.document.element(
            page.document.elements[0].id
        ).type == TYPE_TITRE_1

        # « Oui » : le document est ÉCRASÉ.
        with patch(
            "ui.ouvrage_window"
            ".QMessageBox.warning",
            return_value=(
                QMessageBox.StandardButton.Yes
            )
        ):
            page.generer_ouvrage()

        assert all(
            e.type != TYPE_TITRE_1
            for e in page.document.elements
        )


#
# ==================================================
# Structure manuelle et navigation.
# ==================================================
#

class TestStructureManuelle:

    def test_chapitre_place_les_paragraphes(
        self,
        page
    ):
        """
        Un chapitre inséré au début PLACE les
        paragraphes (plus de « Réserves ») ;
        l'arborescence montre le chapitre avec
        ses paragraphes, le rapport ne signale
        plus de non-placées.
        """

        page.generer_ouvrage()

        page._ajouter_element(
            TYPE_TITRE_1,
            "Chapitre 1"
        )

        assert (
            page.document
            .paragraphes_reserves()
            == []
        )

        libelles = [
            page.arbre.topLevelItem(i).text(0)
            for i in range(
                page.arbre.topLevelItemCount()
            )
        ]

        assert libelles == ["Chapitre 1"]

        chapitre = page.arbre.topLevelItem(0)

        assert chapitre.childCount() == 3

        assert "Non placées" not in (
            page.rapport_zone.toPlainText()
        )

    def test_edition_en_place(
        self,
        page
    ):
        """
        Éditer un titre (chapitre) dans le
        manuscrit modifie l'élément du document —
        l'ouvrage vit sa propre vie.
        """

        page.generer_ouvrage()

        page._ajouter_element(
            TYPE_TITRE_1,
            "Chapitre 1"
        )

        editeur = page.editeurs[
            page.document.elements[0].id
        ]

        assert isinstance(editeur, QLineEdit)

        editeur.setText("Chapitre premier")

        assert (
            page.document
            .elements[0]
            .texte
            == "Chapitre premier"
        )

        assert page.modifie is True

        assert (
            page.sauvegarder_button.isEnabled()
        )

    def test_sauvegarde_et_relecture(
        self,
        page,
        etude_validee
    ):
        """
        Sauvegarder écrit ouvrage.json ; le
        document relu du disque est identique.
        """

        _e, _n, _f, tmp_path = etude_validee

        page.generer_ouvrage()

        page._ajouter_element(
            TYPE_TITRE_1,
            "Chapitre 1"
        )

        page.sauvegarder_document()

        relu = charger_ouvrage(
            tmp_path / "Etude"
        )

        assert relu.to_dict() == (
            page.document.to_dict()
        )

        assert page.modifie is False

    def test_position_insertion_selection(
        self,
        page
    ):
        """
        L'insertion se fait AVANT l'élément
        sélectionné dans l'arborescence (au début
        si rien n'est sélectionné).
        """

        page.generer_ouvrage()

        # Aucune sélection : au début.
        assert page._position_selection() == 0

        # Sélection du dernier paragraphe :
        # insertion juste avant lui.
        dernier = page.document.paragraphes()[-1]

        for i in range(
            page.arbre.topLevelItemCount()
        ):

            noeud = page.arbre.topLevelItem(i)

            for j in range(noeud.childCount()):

                if (
                    noeud.child(j).data(
                        0,
                        Qt.ItemDataRole.UserRole
                    )
                    == dernier.id
                ):

                    page.arbre.setCurrentItem(
                        noeud.child(j)
                    )

        page._ajouter_element(
            TYPE_TITRE_1,
            "Chapitre inséré"
        )

        chapitre = page.document.elements[-2]

        assert chapitre.type == TYPE_TITRE_1

        assert chapitre.texte == "Chapitre inséré"

        assert (
            page.document.elements[-1].id
            == dernier.id
        )


#
# ==================================================
# Rapport : divergences et non-placées.
# ==================================================
#

class TestRapport:

    def test_divergence_signalee(
        self,
        page,
        etude_validee
    ):
        """
        Une version plus récente qu'à la
        génération → le rapport signale «
        Re-reformulé depuis la génération » (le
        document dérivé n'est jamais touché).
        """

        etude, nom, fids, _t = etude_validee

        page.generer_ouvrage()

        assert "Re-reformulé" not in (
            page.rapport_zone.toPlainText()
        )

        ajouter_version_reformulation(
            etude, nom, fids[0],
            "Nouvelle passe après génération"
        )

        page._reconstruire_rapport()

        rapport = (
            page.rapport_zone.toPlainText()
        )

        assert (
            "Re-reformulé depuis la génération"
            in rapport
        )

        assert f"bloc {fids[0]}" in rapport

        # Le document n'est pas touché.
        assert (
            page.document
            .paragraphes()[0]
            .texte
            == f"Reformulation du bloc {fids[0]}"
        )
