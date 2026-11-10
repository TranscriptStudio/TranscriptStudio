# tests/unit/test_p18_10_bible.py
"""
P18.10 — Lecteur de Bible intégré (décision David
du 2026-11-09 ; spec d'autorité BIBLE_JND_V2_2026-
11-09d §7 + §5 invariants 6-9) :

6. la page Bible n'écrit jamais dans un dossier
   d'étude ni dans un projet v1 (seule exception :
   les réglages de l'app — dernier passage) ;
7. les sélecteurs chapitres/versets correspondent
   toujours aux données OSIS de la version affichée
   (jamais de compte en dur) ;
8. « Retour » ramène toujours à la page appelante
   (pile unique) ;
9. un changement de version depuis le lecteur ne
   modifie ni la version de l'étude, ni celle du
   tier réunion, ni la référence de l'ouvrage.

+ dernier passage mémorisé/restauré, version par
défaut = dernière consultée, saisie directe
normalisée P18.1 (ambiguïté → suggestions ;
introuvable → information + autres versions),
aucune version installée → renvoi téléchargeur,
icônes d'accès sur Réunion / éditeur / Ouvrage.
"""

import hashlib
import json
import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

pytestmark = pytest.mark.qt

from PySide6.QtWidgets import QApplication

from services.settings import SettingsManager
from tests.unit.test_p18_5 import (
    OSIS_DARBY,
    OSIS_DARBYR,
)
from tests.unit.test_reformulation_ui import (
    construire_etude_test,
    construire_projet_test,
)


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    yield application


@pytest.fixture
def dossier_bibles(tmp_path):
    dossier = tmp_path / "bibles"
    dossier.mkdir()

    (dossier / "Darby.osis.xml").write_text(
        OSIS_DARBY,
        encoding="utf-8"
    )

    (dossier / "DarbyR.osis.xml").write_text(
        OSIS_DARBYR,
        encoding="utf-8"
    )

    return dossier


@pytest.fixture
def settings(tmp_path):
    return SettingsManager(str(tmp_path / "reglages"))


@pytest.fixture
def page(qapp, tmp_path, dossier_bibles, settings):
    from ui.bible_window import BibleWindow

    fenetre = BibleWindow(
        settings=settings,
        dossier_bibles=dossier_bibles
    )

    yield fenetre

    fenetre.close()


def _hash_dossier(dossier):
    empreintes = {}

    for chemin in sorted(dossier.rglob("*")):

        if chemin.is_file():
            empreintes[str(chemin)] = (
                hashlib.sha256(
                    chemin.read_bytes()
                ).hexdigest()
            )

    return empreintes


class TestSelecteursPilotesParOsis:
    """
    Invariant 7 : les sélecteurs livre/chapitre/
    verset dérivent des données OSIS de la version
    affichée — jamais de listes en dur.
    """

    def test_versions_installees_seulement(
        self,
        page
    ):

        # Deux versions installées = deux entrées
        # (segond1910 n'est PAS installée).
        assert page.combo_version.count() == 2

        donnees = [
            page.combo_version.itemData(i)
            for i in range(page.combo_version.count())
        ]

        assert set(donnees) == {"darby", "darbyR"}

    def test_structure_livre_chapitre_verset(
        self,
        page
    ):

        from services.lecteur_bible import (
            structure_version,
        )

        # Version par défaut = darbyR (premier
        # lancement mémorisé).
        assert (
            page.combo_version.currentData() == "darbyR"
        )

        # Livres = structure OSIS de darbyR.
        structure = structure_version(
            "darbyR",
            page.dossier_bibles
        )

        assert [
            page.combo_livre.itemData(i)
            for i in range(page.combo_livre.count())
        ] == [
            livre["osis_id"] for livre in structure
        ]

        assert [
            page.combo_livre.itemText(i)
            for i in range(page.combo_livre.count())
        ] == ["Genèse", "Jean"]

        # Genèse n'a qu'UN chapitre dans darbyR
        # (la Darby en a deux — versification).
        assert page.combo_chapitre.count() == 1

        # Bascule sur darby : les sélecteurs suivent
        # les données OSIS de la version choisie.
        index_darby = page.combo_version.findData(
            "darby"
        )

        page.combo_version.setCurrentIndex(
            index_darby
        )

        QApplication.processEvents()

        assert page.combo_chapitre.count() == 2

        # Jean 8 : 2 versets en darby, 1 en darbyR.
        index_jean = page.combo_livre.findData(
            "John"
        )

        page.combo_livre.setCurrentIndex(index_jean)

        QApplication.processEvents()

        page.combo_chapitre.setCurrentIndex(0)

        QApplication.processEvents()

        assert page.combo_verset.count() == 2

        # Jamais de compte en dur (66 livres /
        # 1189 chapitres).
        assert page.combo_livre.count() == 2
        assert page.combo_chapitre.count() == 1


class TestDernierPassage:
    """
    P18.10b : dernier passage consulté mémorisé dans
    les réglages et restauré ; version par défaut =
    dernière version consultée.
    """

    def test_premier_lancement(self, page, settings):

        passage = settings.get_dernier_passage_bible()

        assert passage["version"] == "darbyR"
        assert passage["livre"] == 1
        assert passage["chapitre"] == 1
        assert passage["verset"] == 1

    def test_memorise_et_restaure(
        self,
        qapp,
        tmp_path,
        dossier_bibles,
        settings
    ):

        from ui.bible_window import BibleWindow

        fenetre = BibleWindow(
            settings=settings,
            dossier_bibles=dossier_bibles
        )

        try:

            # Consulte darby, Jean 8, v2.
            fenetre.combo_version.setCurrentIndex(
                fenetre.combo_version.findData("darby")
            )

            QApplication.processEvents()

            fenetre.combo_livre.setCurrentIndex(
                fenetre.combo_livre.findData("John")
            )

            QApplication.processEvents()

            fenetre.combo_verset.setCurrentIndex(1)

            QApplication.processEvents()

            passage = (
                settings.get_dernier_passage_bible()
            )

            assert passage["version"] == "darby"
            assert passage["livre_osis"] == "John"
            assert passage["livre"] == 2
            assert passage["chapitre"] == 8
            assert passage["verset"] == 2

        finally:
            fenetre.close()

        # Réouverture : passage restauré, version par
        # défaut = dernière consultée (darby).
        fenetre2 = BibleWindow(
            settings=settings,
            dossier_bibles=dossier_bibles
        )

        try:

            assert (
                fenetre2.combo_version.currentData()
                == "darby"
            )

            assert (
                fenetre2.combo_livre.currentData()
                == "John"
            )

            assert (
                fenetre2.combo_chapitre.currentData()
                == 8
            )

            assert (
                fenetre2.combo_verset.currentData() == 2
            )

        finally:
            fenetre2.close()


class TestSaisieDirecte:
    """
    P18.10c : saisie directe d'une référence,
    normalisée P18.1 ; ambiguïté → suggestions ;
    introuvable dans la version → information +
    autres versions installées.
    """

    def test_reference_exacte(self, page):

        from services.lecteur_bible import (
            resoudre_saisie,
        )
        from services.jnd import charger_bible

        bible = charger_bible(
            page.dossier_bibles / "Darby.osis.xml"
        )

        resultat = resoudre_saisie(
            "Jn 8:1",
            bible,
            {}
        )

        assert resultat["statut"] == "ok"
        assert str(resultat["reference"]) == "Jean 8.1"
        assert resultat["existe"] is True

    def test_introuvable_versification(self, page):

        from services.lecteur_bible import (
            resoudre_saisie,
        )
        from services.jnd import charger_bible

        # darbyR : Jean 8.1 n'existe pas.
        bible = charger_bible(
            page.dossier_bibles / "DarbyR.osis.xml"
        )

        autres = {
            "darby": charger_bible(
                page.dossier_bibles / "Darby.osis.xml"
            )
        }

        resultat = resoudre_saisie(
            "Jean 8.1",
            bible,
            autres
        )

        assert resultat["statut"] == "ok"
        assert resultat["existe"] is False
        assert resultat["existe_ailleurs"] == ["darby"]

    def test_ambiguite_suggestions(self, page):

        from services.lecteur_bible import (
            resoudre_saisie,
        )
        from services.jnd import charger_bible

        bible = charger_bible(
            page.dossier_bibles / "Darby.osis.xml"
        )

        resultat = resoudre_saisie(
            "Genèse 1.1 et Jean 8.2",
            bible,
            {}
        )

        assert resultat["statut"] == "ambigu"
        assert len(resultat["suggestions"]) == 2

    def test_aller_saisie_navigue(
        self,
        page,
        monkeypatch
    ):

        from PySide6.QtWidgets import QInputDialog

        # Version darby (Jean 8.1 existe).
        page.combo_version.setCurrentIndex(
            page.combo_version.findData("darby")
        )

        QApplication.processEvents()

        page.saisie.setText("Jn 8:1")

        page.aller_saisie()

        assert page.combo_livre.currentData() == "John"
        assert page.combo_chapitre.currentData() == 8
        assert page.combo_verset.currentData() == 1

        # La cible est surlignée dans le chapitre
        # (ancre + span de surlignage dans le HTML
        # source affiché).
        assert page.verset_surligne == 1
        assert 'name="v1"' in page.dernier_html
        assert "rgba(59,158,255,60)" in page.dernier_html


class TestAucuneVersionInstallee:
    """
    P18.10d : aucune version installée → message +
    renvoi vers le téléchargeur des réglages.
    """

    def test_renvoi_telechargeur(
        self,
        qapp,
        tmp_path,
        settings
    ):

        from ui.bible_window import BibleWindow

        vide = tmp_path / "bibles_vide"
        vide.mkdir()

        fenetre = BibleWindow(
            settings=settings,
            dossier_bibles=vide
        )

        try:

            assert fenetre.combo_version.count() == 0

            assert (
                fenetre.telechargeur_button
                .isVisibleTo(fenetre)
            )

            assert "téléchargeur" in (
                fenetre.avertissement_label.text()
            )

        finally:
            fenetre.close()


class TestInvariant6AucuneEcritureHorsReglages:
    """
    Invariant 6 : la page Bible n'écrit JAMAIS dans
    un dossier d'étude ni dans un projet v1.
    """

    def test_consultation_ne_touche_rien(
        self,
        qapp,
        tmp_path,
        dossier_bibles,
        settings
    ):

        _p, _pv, _e, _n = construire_etude_test(
            tmp_path
        )

        dossier_etude = tmp_path / "Etude"
        dossier_projet = tmp_path / "2026-10-13_Luc1b"

        avant_etude = _hash_dossier(dossier_etude)
        avant_projet = _hash_dossier(dossier_projet)

        from ui.bible_window import BibleWindow

        fenetre = BibleWindow(
            settings=settings,
            dossier_bibles=dossier_bibles
        )

        try:

            fenetre.combo_version.setCurrentIndex(0)
            QApplication.processEvents()

            fenetre.combo_livre.setCurrentIndex(1)
            QApplication.processEvents()

            fenetre.saisie.setText("Gen 1.1")
            fenetre.aller_saisie()

        finally:
            fenetre.close()

        assert _hash_dossier(dossier_etude) == (
            avant_etude
        )

        assert _hash_dossier(dossier_projet) == (
            avant_projet
        )


class TestInvariant8RetourPageAppelante:
    """
    Invariant 8 : « Retour » depuis la page Bible
    ramène toujours à la page appelante (pile
    unique inchangée — une seule page « bible »).
    """

    def test_retour(self, qapp, tmp_path, settings):

        from ui.app_window import AppWindow

        _p, _pv, _e, _n = construire_etude_test(
            tmp_path
        )

        settings.add_recent_etude(
            str(tmp_path / "Etude")
        )

        fenetre_app = AppWindow(settings=settings)

        try:

            page_etude = fenetre_app.ouvrir_etude(
                tmp_path / "Etude"
            )

            page_bible = fenetre_app.ouvrir_bible()

            from ui.bible_window import BibleWindow

            assert isinstance(
                page_bible,
                BibleWindow
            )

            assert (
                fenetre_app.page_active()
                is page_bible
            )

            cles_bible = [
                cle
                for cle in fenetre_app.cles_ouvertes()
                if cle[0] == "bible"
            ]

            assert len(cles_bible) == 1

            # Ouvrir deux fois : toujours UNE page.
            fenetre_app.ouvrir_bible()

            cles_bible = [
                cle
                for cle in fenetre_app.cles_ouvertes()
                if cle[0] == "bible"
            ]

            assert len(cles_bible) == 1

            retour = fenetre_app.retour_bible()

            assert retour is page_etude

            assert (
                fenetre_app.page_active()
                is page_etude
            )

        finally:
            fenetre_app.close()


class TestInvariant9ChangementVersionSansEcritureEnRetour:
    """
    Invariant 9 : un changement de version depuis le
    lecteur ne modifie ni la version de l'étude, ni
    celle du tier réunion, ni la référence d'uniformité
    de l'ouvrage (aucune écriture en retour).
    """

    def test_changement_version(
        self,
        qapp,
        tmp_path,
        dossier_bibles,
        settings
    ):

        from services.etude_io import (
            ouvrir_etude,
        )
        from services.tier_reunion import (
            sauvegarder_tier,
        )

        _p, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        etude_disco = ouvrir_etude(tmp_path / "Etude")

        # Version de l'étude (mémoire) + du tier
        # (persistée explicitement par le test).
        etude_disco.parametres.bible["version"] = (
            "segond1910"
        )

        tier = etude_disco.tier_de(nom)

        tier.parametres.bible["version"] = "darby"

        sauvegarder_tier(tier)

        avant_etude = _hash_dossier(
            tmp_path / "Etude"
        )

        avant_projet = _hash_dossier(
            tmp_path / "2026-10-13_Luc1b"
        )

        from ui.bible_window import BibleWindow

        fenetre = BibleWindow(
            settings=settings,
            dossier_bibles=dossier_bibles
        )

        try:

            # Change de version dans le lecteur.
            fenetre.combo_version.setCurrentIndex(
                fenetre.combo_version.findData("darby")
            )

            QApplication.processEvents()

        finally:
            fenetre.close()

        # Aucun écriture en retour.
        assert _hash_dossier(
            tmp_path / "Etude"
        ) == avant_etude

        assert _hash_dossier(
            tmp_path / "2026-10-13_Luc1b"
        ) == avant_projet

        # Ni la version de l'étude (mémoire), ni
        # celle du tier (persistée) n'ont bougé.
        assert (
            etude_disco.parametres.bible["version"]
            == "segond1910"
        )

        recharge = ouvrir_etude(tmp_path / "Etude")

        assert (
            recharge.tier_de(nom)
            .parametres.bible["version"]
            == "darby"
        )

        # Seuls les réglages de l'app ont bougé.
        assert (
            settings.get_dernier_passage_bible()
            ["version"]
            == "darby"
        )


class TestIconesAcces:
    """
    P18.10a : icône d'accès au lecteur sur la page
    Réunion, l'éditeur de transcription et la page
    Ouvrage.
    """

    def test_page_reunion(
        self,
        qapp,
        tmp_path,
        settings
    ):

        from services.etude_io import ouvrir_etude
        from ui.reunion_window import ReunionWindow

        _p, _pv, _e, nom = construire_etude_test(
            tmp_path
        )

        etude_disco = ouvrir_etude(tmp_path / "Etude")

        fenetre = ReunionWindow(
            _pv,
            settings=settings,
            etude=etude_disco,
            nom=nom
        )

        try:
            assert hasattr(fenetre, "bible_button")
            assert "Bible" in fenetre.bible_button.text()
        finally:
            fenetre.close()

    def test_page_ouvrage(
        self,
        qapp,
        tmp_path,
        settings
    ):

        from services.etude_io import ouvrir_etude
        from ui.ouvrage_window import OuvrageWindow

        _p, _pv, _e, _n = construire_etude_test(
            tmp_path
        )

        etude_disco = ouvrir_etude(tmp_path / "Etude")

        fenetre = OuvrageWindow(
            etude_disco,
            settings=settings
        )

        try:
            assert hasattr(fenetre, "bible_button")
            assert "Bible" in fenetre.bible_button.text()
        finally:
            fenetre.close()

    def test_editeur_transcription(
        self,
        qapp,
        tmp_path,
        settings
    ):

        from ui.main_window import MainWindow

        _projet, projet_v1 = construire_projet_test(
            tmp_path
        )

        fenetre = MainWindow(
            projet_v1,
            settings=settings
        )

        try:
            assert hasattr(fenetre, "bible_button")
            assert (
                fenetre.bible_button.toolTip()
            )
        finally:
            fenetre.close()
