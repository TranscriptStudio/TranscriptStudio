# tests/unit/test_p18_9_etude.py
"""
P18.9 — Correctifs page Étude (relecture David du
2026-11-09 ; feuille d'autorité
SPEC_PAGE_ETUDE_ET_SYNTHESE_MODIFS_2026-11-09d §2,
invariants 1-7) :

1. clic gauche sur le corps d'une tuile = glisser-
   déposer UNIQUEMENT (aucune navigation), ordre
   persisté (etude.json) ;
2. plus de flèche de réordonnancement ni de bouton
   « Ouvrir » sur la page ;
3. clic droit sur une tuile = UNIQUEMENT le menu
   contextuel (étapes, « Retirer la réunion »,
   « Relocaliser ») ;
4. badge Bible : une seule version, jamais de champ
   « versification » ; info-bulle sans commentaire
   de spec ;
5. bouton « Édition ouvrage final » à droite de
   « ＋ Ajouter une réunion… » ;
6. bandeau/labels à la teinte EXACTE du fond de page,
   sur toutes les pages concernées (transverse) ;
7. conteneur des tuiles défilant indépendamment ;
   rehaussement au survol non rogné sur la première
   tuile.
"""

import json
import os
import shutil

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

pytestmark = pytest.mark.qt

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
)

from services.etude_io import (
    ajouter_reunion,
    creer_etude,
    ouvrir_etude,
    sauvegarder_etude,
)
from services.settings import SettingsManager
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
)


def _creer_projet_v1(dossier_parent, nom: str):
    dossier = dossier_parent / nom
    dossier.mkdir(parents=True)

    (dossier / "project.sttproj").write_text(
        json.dumps({
            "project_format_version": 1,
            "name": nom,
            "audio_file": "audio.wav",
            "transcription_id": None,
            "language_code": "fr",
            "duration_seconds": 100.0,
            "modified": False,
            "speakers": [],
            "words": [],
            "blocks": [],
            "original_elevenlabs_response": {},
        }),
        encoding="utf-8"
    )

    return dossier


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


@pytest.fixture
def page(qapp, tmp_path):

    _p, _pv, _e, _n = construire_etude_test(
        tmp_path
    )

    etude = ouvrir_etude(tmp_path / "Etude")

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

    sauvegarder_etude(etude)

    from ui.etude_window import EtudeWindow

    fenetre = EtudeWindow(
        tmp_path / "Etude",
        settings=SettingsManager(
            str(tmp_path / "reglages")
        )
    )

    yield fenetre, tmp_path, [ _n, nom2 ]

    fenetre.close()


def _tuile(fenetre, index=0):
    item = fenetre.reunions_liste.item(index)
    return fenetre.reunions_liste.itemWidget(item)


class TestClicGaucheDeplacementUniquement:
    """
    Invariant 1 : le clic gauche sur le corps d'une
    tuile ne déclenche aucune navigation ni
    ouverture ; seul le glisser-déposer modifie
    l'ordre, et l'ordre persiste (etude.json).
    """

    def test_clic_gauche_ne_navigue_pas(self, page, monkeypatch):

        fenetre, _tmp, noms = page

        appels = []

        monkeypatch.setattr(
            fenetre,
            "ouvrir_reunion_editeur",
            lambda *a: appels.append(a)
        )

        monkeypatch.setattr(
            fenetre,
            "_ouvrir_etape",
            lambda *a: appels.append(a)
        )

        tuile = _tuile(fenetre, 0)

        evenement = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            tuile.rect().center(),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        tuile.mousePressEvent(evenement)

        assert appels == []
        # L'événement est ignoré : le drag interne
        # peut s'amorcer.
        assert not evenement.isAccepted()

    def test_glisser_deposer_persiste(self, page):

        fenetre, tmp_path, noms = page

        from ui.etude_window import (
            ListeReunionsEtude,
        )

        assert isinstance(
            fenetre.reunions_liste,
            ListeReunionsEtude
        )

        assert (
            fenetre.reunions_liste.dragDropMode()
            == ListeReunionsEtude.DragDropMode.InternalMove
        )

        # Simule le dépôt dans l'ordre inverse.
        inverse = list(reversed(noms))

        fenetre._persister_ordre(inverse)

        assert (
            fenetre.etude.etude.ordre_reunions
            == inverse
        )

        # Persisté dans etude.json.
        recharge = ouvrir_etude(tmp_path / "Etude")

        assert (
            recharge.etude.ordre_reunions
            == inverse
        )

        # Ordre non valide (permutation incomplète) :
        # ignoré, la liste est reconstruite.
        fenetre._persister_ordre([noms[0]])

        assert (
            fenetre.etude.etude.ordre_reunions
            == inverse
        )


class TestPlusDeBoutonsTuile:
    """
    Invariant 2 : la page Étude n'affiche ni flèche
    de réordonnancement ni bouton « Ouvrir ».
    """

    def test_tuile_sans_boutons(self, page):

        fenetre = page[0]

        for index in range(fenetre.reunions_liste.count()):

            tuile = _tuile(fenetre, index)

            textes = [
                b.text()
                for b in tuile.findChildren(QPushButton)
                # Les pastilles du stepper restent
                # (cliquables) — seules les flèches
                # et « Ouvrir » disparaissent.
                if b.parent() is not None
            ]

            for interdit in ("Ouvrir", "↑", "↓"):
                assert interdit not in textes

        tous = [
            b.text()
            for b in fenetre.findChildren(QPushButton)
        ]

        assert "Ouvrir" not in tous
        assert "↑" not in tous
        assert "↓" not in tous

    def test_stepper_cliquable(self, page):
        """
        Navigation par tuile : le stepper de la
        tuile est cliquable (pastilles = liens vers
        les étapes de la page Réunion).
        """

        from ui.stepper import StepperBar

        fenetre = page[0]

        steppers = fenetre.findChildren(StepperBar)

        assert steppers

        for stepper in steppers:
            assert stepper._cliquable is True


class TestMenuContextuel:
    """
    Invariant 3 : le clic droit sur une tuile
    n'ouvre que le menu contextuel (étapes,
    « Retirer la réunion », « Relocaliser »).
    """

    def test_menu_tuile(self, page):

        fenetre, _tmp, noms = page

        item = fenetre.reunions_liste.item(0)

        menu = fenetre._construire_menu_tuile(
            noms[0],
            item
        )

        textes = [
            a.text() for a in menu.actions()
        ]

        # Accès aux étapes (idem clic stepper).
        for etape in (
            "Transcription",
            "Reformulation",
            "Résumé",
        ):
            assert etape in textes

        assert "Retirer la réunion" in textes
        assert "Relocaliser…" in textes

    def test_clic_droit_ouvre_le_menu(self, page, monkeypatch):

        fenetre, _tmp, noms = page

        execs = []

        # QMenu.exec n'est pas monkeypatchable sous
        # PySide6 : on intercepte _executer_menu.
        monkeypatch.setattr(
            fenetre,
            "_executer_menu",
            lambda menu, pos: execs.append(menu)
        )

        item = fenetre.reunions_liste.item(0)
        rect = fenetre.reunions_liste.visualItemRect(item)

        fenetre._sur_menu_contextuel_liste(
            rect.center()
        )

        assert len(execs) == 1

        textes = [
            a.text() for a in execs[0].actions()
        ]

        assert "Retirer la réunion" in textes

        # Clic droit hors tuile : aucun menu.
        execs.clear()

        fenetre._sur_menu_contextuel_liste(
            rect.bottomLeft() + QPoint(-500, 0)
        )

        assert execs == []


class TestBadgeSimplifie:
    """
    Invariant 4 (P18.9) : le badge Bible n'affiche qu'une
    version, jamais de champ « versification » ;
    l'info-bulle ne contient aucun commentaire de
    spec.

    P18.9-bis.c (série 2, prime sur la série 1) : la
    page Étude n'affiche PLUS aucune version de Bible —
    le badge d'en-tête et la mention sous la synthèse
    sont supprimés (invariant 17).
    """

    def test_badge(self, page):

        from services.bibles import (
            badge_bible_etude,
        )

        fenetre, _tmp, _noms = page

        texte, tooltip = badge_bible_etude(
            fenetre.etude
        )

        assert texte == "Bible : Darby révisée"
        assert "versification" not in texte
        assert "P18.5" not in tooltip
        assert "versification" not in tooltip.lower()

        # P18.9-bis.c : plus de badge sur la page Étude.
        assert not hasattr(fenetre, "badge_bible_label")


class TestBoutonOuvrage:
    """
    Invariant 5 : le bouton d'accès à l'ouvrage est
    libellé « Édition ouvrage final » et placé à
    droite de « ＋ Ajouter une réunion… ».
    """

    def test_position(self, page):

        fenetre = page[0]

        assert (
            fenetre.ouvrage_button.text()
            == "Édition ouvrage final"
        )

        layout = fenetre.entete_reunions

        index_ajouter = layout.indexOf(
            fenetre.ajouter_button
        )

        index_ouvrage = layout.indexOf(
            fenetre.ouvrage_button
        )

        assert index_ajouter != -1
        assert index_ouvrage > index_ajouter


class TestFondsDePage:
    """
    Invariant 6 : bandeau supérieur et labels à la
    teinte identique au fond de page, sur toutes les
    pages concernées par le reliquat.
    """

    def test_helper(self):

        from services.theme_manager import (
            FOND_PAGE_CLAIR,
            FOND_PAGE_SOMBRE,
            feuille_fond_page,
        )

        for sombre, fond in (
            (True, FOND_PAGE_SOMBRE),
            (False, FOND_PAGE_CLAIR),
        ):

            feuille = feuille_fond_page(
                "PageTest",
                sombre
            )

            assert fond in feuille
            assert "PageTest > QWidget" in feuille
            assert "PageTest QLabel" in feuille
            assert feuille.count("transparent") >= 3

    def test_page_etude(self, page):

        fenetre = page[0]

        feuille = fenetre.styleSheet()

        assert "EtudeWindow {" in feuille
        assert "EtudeWindow > QWidget" in feuille
        assert "EtudeWindow QLabel" in feuille
        assert "background: transparent" in feuille

    def test_fond_reunion_ouvrage(self, qapp, tmp_path):

        _p, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        etude_disco = ouvrir_etude(tmp_path / "Etude")

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        from ui.reunion_window import ReunionWindow

        page_reunion = ReunionWindow(
            _pv,
            settings=settings,
            etude=etude_disco,
            nom=nom,
        )

        try:

            feuille = page_reunion.styleSheet()

            assert "ReunionWindow {" in feuille
            assert (
                "ReunionWindow > QWidget"
                in feuille
            )

            from ui.ouvrage_window import (
                OuvrageWindow,
            )

            page_ouvrage = OuvrageWindow(
                etude_disco,
                settings=settings,
            )

            try:

                feuille = page_ouvrage.styleSheet()

                assert "OuvrageWindow {" in feuille
                assert (
                    "OuvrageWindow > QWidget"
                    in feuille
                )

            finally:
                page_ouvrage.close()

        finally:
            page_reunion.close()


class TestScrollEtSurvol:
    """
    Invariant 7 : le conteneur des tuiles défile
    indépendamment ; l'effet de rehaussement au
    survol est visible intégralement, y compris pour
    la première tuile.
    """

    def test_marges_survol(self, page):

        from ui.tuiles import ELEVATION_SURVOL

        fenetre = page[0]

        marges = fenetre.reunions_liste.viewportMargins()

        assert marges.top() >= ELEVATION_SURVOL
        assert marges.bottom() >= ELEVATION_SURVOL

    def test_defilement_independant(self, qapp, tmp_path):

        # Étude de 35 réunions.
        etude = creer_etude(
            tmp_path / "Etude",
            "Étude longue"
        )

        base = _creer_projet_v1(
            tmp_path,
            "2026-10-13_Luc1b"
        )

        for i in range(35):

            if i == 0:
                dossier = base
            else:
                dossier = tmp_path / f"reunion_{i:02d}"
                shutil.copytree(base, dossier)

            ajouter_reunion(
                etude,
                dossier,
                f"Réunion {i + 1}"
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

            fenetre.resize(700, 480)
            fenetre.show()

            QApplication.processEvents()

            assert (
                fenetre.reunions_liste.count() == 35
            )

            # Le conteneur défile : la somme des
            # hauteurs des tuiles dépasse la hauteur
            # du conteneur.
            hauteur_totale = sum(
                fenetre.reunions_liste
                .visualItemRect(
                    fenetre.reunions_liste.item(i)
                )
                .height()
                for i in range(35)
            )

            assert (
                fenetre.reunions_liste.height()
                < hauteur_totale
            )

            assert (
                fenetre.reunions_liste
                .verticalScrollBar()
                .maximum()
                > 0
            )

        finally:
            fenetre.close()
