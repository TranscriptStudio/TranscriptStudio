# tests/unit/test_p20_1_mobilite.py
"""
P20.1 — Mobilité inter-blocs des paragraphes de
l'ouvrage : déplacement (à travers blocs et
sections, provenance conservée), suppression,
édition libre (déjà en place), et contrôle des
renvois orphelins après déplacement (détection
locale, signalement uniquement).
"""

import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

pytestmark = pytest.mark.qt

from PySide6.QtWidgets import QApplication

from models.ouvrage import (
    ElementOuvrage,
    ProvenanceParagraphe,
    TYPE_PARAGRAPHE,
    TYPE_SEPARATEUR,
    TYPE_TITRE_1,
    DocumentOuvrage,
)
from services.ouvrage_document import (
    FusionPenseesError,
    controler_renvois_apres_deplacement,
    deplacer_element,
    detecter_renvois,
    supprimer_element,
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


def _provenance(reunion="r1", fid=1, numero=1):
    return ProvenanceParagraphe(
        reunion=reunion,
        fid=fid,
        numero_reunion=numero,
        date_reunion="2026-10-13",
        locuteurs="Philippe",
        numero_version=1,
        horodatage_version="2026-10-13T10:00:00",
    )


def _document_simple() -> DocumentOuvrage:
    """
    Document : titre_1 « Chapitre 1 », séparateur,
    3 paragraphes (p1..p3) avec provenances.
    """

    doc = DocumentOuvrage(titre="Ouvrage test")

    doc.elements.append(
        ElementOuvrage(
            id="t1_1",
            type=TYPE_TITRE_1,
            texte="Chapitre 1",
        )
    )

    doc.elements.append(
        ElementOuvrage(
            id="sep1",
            type=TYPE_SEPARATEUR,
        )
    )

    for i, texte in enumerate(
        [
            "Première pensée du chapitre.",
            "Comme on l'a dit plus haut, la grâce abonde.",
            "Troisième pensée, indépendante.",
        ],
        start=1,
    ):
        doc.elements.append(
            ElementOuvrage(
                id=f"p{i}",
                type=TYPE_PARAGRAPHE,
                texte=texte,
                provenances=[_provenance(fid=i)],
            )
        )

    return doc


class TestDeplacement:

    def test_deplacement_traverse_sections(self):
        """
        Un paragraphe peut être déplacé à travers
        blocs et sections ; sa provenance est
        conservée (l'élément entier est déplacé).
        """

        doc = _document_simple()

        # p3 (dernier) -> position 1 (juste après le
        # titre, avant le séparateur).
        nouvelle = deplacer_element(doc, "p3", 1)

        assert nouvelle == 1

        assert [e.id for e in doc.elements] == [
            "t1_1",
            "p3",
            "sep1",
            "p1",
            "p2",
        ]

        # Provenance conservée.
        p3 = doc.element("p3")

        assert p3.provenances[0].fid == 3
        assert p3.provenances[0].reunion == "r1"
        assert p3.texte == (
            "Troisième pensée, indépendante."
        )

    def test_deplacement_bornes(self):

        doc = _document_simple()

        # Position négative -> 0.
        assert deplacer_element(doc, "p1", -5) == 0
        assert doc.elements[0].id == "p1"

        # Au-delà de la fin -> dernière position.
        assert (
            deplacer_element(doc, "p1", 99)
            == len(doc.elements) - 1
        )

    def test_deplacement_introuvable(self):

        doc = _document_simple()

        with pytest.raises(FusionPenseesError):
            deplacer_element(doc, "inconnu", 0)


class TestSuppression:

    def test_suppression(self):

        doc = _document_simple()

        retire = supprimer_element(doc, "p2")

        assert retire.id == "p2"
        assert "p2" not in [e.id for e in doc.elements]

        with pytest.raises(FusionPenseesError):
            supprimer_element(doc, "p2")


class TestRenvoisOrphelins:
    """
    Contrôle des renvois orphelins après
    déplacement : détection locale (« comme on
    l'a dit »…), signalement uniquement.
    """

    def test_detection_locale(self):

        assert detecter_renvois(
            "Comme on l'a dit, la grâce abonde."
        )

        assert detecter_renvois(
            "Nous l'avons vu précédemment."
        )

        assert detecter_renvois(
            "Cela a été dit plus haut."
        )

        assert not detecter_renvois(
            "La grâce de Dieu abonde."
        )

    def test_signalement_apres_deplacement(self):

        doc = _document_simple()

        # p2 contient un renvoi ; il est déplacé en
        # position 0 (avant son précédent p1) : le
        # renvoi peut être orphelin.
        ancienne = doc.elements.index(doc.element("p2"))

        precedent_avant = doc.elements[ancienne - 1].id

        deplacer_element(doc, "p2", 0)

        signalements = (
            controler_renvois_apres_deplacement(
                doc,
                "p2",
                ancienne,
                precedent_avant_id=precedent_avant
            )
        )

        assert len(signalements) == 1
        assert signalements[0]["id"] == "p2"
        assert signalements[0]["precedent_avant"] == "p1"
        assert signalements[0]["precedent_apres"] is None
        assert signalements[0]["renvois"]

    def test_pas_de_signalement_si_inchange(self):

        doc = _document_simple()

        ancienne = doc.elements.index(doc.element("p2"))

        # Pas de déplacement.
        assert controler_renvois_apres_deplacement(
            doc, "p2", ancienne
        ) == []

    def test_pas_de_signalement_si_pas_de_renvoi(self):

        doc = _document_simple()

        ancienne = doc.elements.index(doc.element("p1"))

        deplacer_element(doc, "p1", 4)

        assert controler_renvois_apres_deplacement(
            doc, "p1", ancienne
        ) == []


class TestUiMobilite:
    """
    Page Ouvrage : boutons Monter / Descendre /
    Supprimer sur l'élément sélectionné ; le
    signalement des renvois orphelins apparaît dans
    le rapport.
    """

    def test_boutons_et_deplacement(self, qapp, tmp_path):

        from services.etude_io import (
            ajouter_version_reformulation,
            ouvrir_etude,
            sauvegarder_etude,
            valider_version_reformulation,
        )
        from services.ouvrage_document import (
            generer_document,
            sauvegarder_ouvrage,
        )
        from ui.ouvrage_window import OuvrageWindow

        _p, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        fids = [
            e.fid
            for e in etude.registre.entrees.values()
            if e.reunion == nom
        ]

        for fid in fids:

            v = ajouter_version_reformulation(
                etude,
                nom,
                fid,
                f"Reformulation du bloc {fid}. "
                + (
                    "Comme on l'a dit, la grâce abonde."
                    if fid == fids[min(1, len(fids) - 1)]
                    else "Pensée du bloc."
                ),
            )

            valider_version_reformulation(
                etude,
                nom,
                fid,
                numero=v.numero,
                validateur="Test",
            )

        sauvegarder_etude(etude)

        etude_disco = ouvrir_etude(tmp_path / "Etude")

        document = generer_document(etude_disco)

        sauvegarder_ouvrage(
            document,
            etude_disco.dossier
        )

        fenetre = OuvrageWindow(
            etude_disco,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            ),
        )

        try:

            assert hasattr(fenetre, "monter_button")
            assert hasattr(fenetre, "descendre_button")
            assert hasattr(fenetre, "supprimer_button")

            paragraphes = document.paragraphes()

            assert len(paragraphes) >= 2

            # Sélectionne le deuxième paragraphe.
            from PySide6.QtCore import Qt

            item = None

            def _trouver(noeud):
                for j in range(noeud.childCount()):
                    enfant = noeud.child(j)
                    if (
                        enfant.data(
                            0,
                            Qt.ItemDataRole.UserRole
                        ) == paragraphes[1].id
                    ):
                        return enfant
                    r = _trouver(enfant)
                    if r is not None:
                        return r
                return None

            for i in range(fenetre.arbre.topLevelItemCount()):
                item = _trouver(
                    fenetre.arbre.topLevelItem(i)
                )
                if item is not None:
                    break

            assert item is not None

            fenetre.arbre.setCurrentItem(item)

            assert fenetre.monter_button.isEnabled()

            # Monter : le paragraphe remonte d'une
            # position, provenance conservée.
            fenetre.monter_selection()

            doc_fenetre = fenetre.document

            nouvelle_position = doc_fenetre.elements.index(
                doc_fenetre.element(paragraphes[1].id)
            )

            assert nouvelle_position == 0

            assert doc_fenetre.element(
                paragraphes[1].id
            ).provenances

            # Le rapport affiche le signalement de
            # renvoi orphelin (le bloc contient
            # « comme on l'a dit » et son précédent a
            # changé).
            assert fenetre._signalements_renvois

            assert "orphelin" in (
                fenetre.rapport_zone.toPlainText()
            )

        finally:
            fenetre.close()
