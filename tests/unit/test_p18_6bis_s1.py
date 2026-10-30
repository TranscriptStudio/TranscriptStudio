"""
Tests P18.6-bis, SÉRIE 1 (spec
SPEC_NAVIGATION_MODIFS_V2_2026-10-30c §1-17) :
grandes tuiles du hub (textes exacts, « Version
2.0 », vue Études dédiée), page Réunion sans
bandeau app ni onglets ni « Retour à l'étude »,
badge Bible au nom court, page Étude (badge court,
date de réunion, titres lisibles, boutons par
tuile retirés, pluriels propres, en-tête de
liste).

Invariants complémentaires couverts : 1, 2, 3, 4.
"""

import os
import time
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
    QTabBar,
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
def hub(qapp, tmp_path):

    from services.llm.catalogue import (
        catalogue_par_defaut,
    )
    from ui.home_window import HomeWindow

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    with patch(
        "services.llm.catalogue.charger_catalogue",
        return_value=catalogue_par_defaut(),
    ):
        accueil = HomeWindow(settings=settings)

    yield accueil, settings

    accueil.close()


#
# ==================================================
# Hub : grandes tuiles, textes exacts (§1-§4).
# ==================================================
#

class TestHubSerie1:

    def test_grandes_tuiles_textes_exacts(self, hub):

        accueil, _s = hub

        assert (
            accueil.tuile_nouvelle.titre
            == "Nouvelle transcription"
        )

        assert (
            accueil.tuile_reprendre.titre
            == "Reprendre une réunion"
        )

        assert (
            accueil.tuile_etudes.titre
            == "Études"
        )

        # Descriptions exactes (§1).
        descriptions = {
            accueil.tuile_nouvelle: (
                "Prétraiter un audio (optionnel), "
                "lancer la transcription et "
                "éventuellement poursuivre le "
                "processus (reformulation, etc.)."
            ),
            accueil.tuile_reprendre: (
                "Reprendre le travail où vous "
                "l'avez laissé : correction de "
                "transcription, reformulation, "
                "résumé, etc."
            ),
            accueil.tuile_etudes: (
                "Créer une étude, ouvrir et gérer "
                "une étude existante. Une étude est "
                "un regroupement de réunions ayant "
                "pour objet un thème spécifique."
            ),
        }

        labels = [
            l.text()
            for l in accueil.findChildren(QLabel)
        ]

        for attendu in descriptions.values():
            assert attendu in labels

    def test_sous_titre_et_version(self, hub):

        accueil, _s = hub

        # §2 : sous-titre exact.
        assert accueil.subtitle_label.text() == (
            "Prétraitement audio, transcription et "
            "reformulation assistés"
        )

        # §3 : « Version 2.0 », sans date.
        assert (
            accueil.version_label.text()
            == "Version 2.0"
        )

    def test_hub_sans_section_etudes(self, hub):
        """
        Invariant 1 : le hub n'affiche JAMAIS la
        liste des études — la tuile « Études »
        ouvre une vue dédiée.
        """

        accueil, _s = hub

        assert not hasattr(
            accueil,
            "recent_etudes"
        )

        assert not hasattr(
            accueil,
            "new_etude_button"
        )

        from ui.etudes_window import EtudesWindow

        assert not (
            accueil
            .findChildren(EtudesWindow)
        )

    def test_vue_etudes_dediee(
        self,
        qapp,
        tmp_path
    ):
        """
        La tuile « Études » ouvre la vue dédiée via
        la pile : liste, « Nouvelle étude »,
        « Ouvrir depuis un dossier… ».
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

            accueil = fenetre_app.accueil

            accueil.ouvrir_vue_etudes()

            from ui.etudes_window import (
                EtudesWindow
            )

            vue = fenetre_app.page_active()

            assert isinstance(vue, EtudesWindow)

            boutons = [
                b.text()
                for b in (
                    vue.findChildren(QPushButton)
                )
            ]

            assert "Nouvelle étude" in boutons
            assert (
                "Ouvrir depuis un dossier…"
                in boutons
            )

            assert (
                "Ouvrir l'étude sélectionnée"
                in boutons
            )

            # L'étude récente y figure.
            assert vue.liste_etudes.count() == 1

        finally:
            fenetre_app.close()


#
# ==================================================
# Page Réunion : pas de bandeau, pas d'onglets,
# pas de « Retour à l'étude » (§6-§8) — invariant 2.
# ==================================================
#

class TestReunionSerie1:

    def test_pas_de_bandeau_ni_onglets(
        self,
        qapp,
        tmp_path
    ):
        """
        Invariant 2 : aucun bandeau app hors
        accueil, aucune rangée d'onglets sur la
        page Réunion.
        """

        projet, projet_v1, etude, nom = (
            construire_etude_test(tmp_path)
        )

        from ui.reunion_window import ReunionWindow

        fenetre = ReunionWindow(
            projet_v1,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            ),
            etude=etude,
            nom=nom
        )

        try:

            bandeaux = [
                w for w in (
                    fenetre.findChildren(QWidget)
                )
                if w.objectName() == "bandeau_app"
            ]

            assert bandeaux == []

            assert not (
                fenetre.findChildren(QTabBar)
            )

        finally:
            fenetre.close()

    def test_badge_nom_court(
        self,
        qapp,
        tmp_path
    ):
        """
        §9 : « Étude « … » · Bible : Darby
        révisée » — nom court, pas de doublon
        « Bible : Bible ».
        """

        projet, projet_v1, etude, nom = (
            construire_etude_test(tmp_path)
        )

        from ui.reunion_window import ReunionWindow

        fenetre = ReunionWindow(
            projet_v1,
            settings=SettingsManager(
                str(tmp_path / "reglages")
            ),
            etude=etude,
            nom=nom
        )

        try:

            badge = fenetre.badge_label.text()

            assert badge.startswith(
                "Étude « Évangile de Luc »"
            )

            assert "Bible : Darby révisée" in badge

            assert "Bible : Bible" not in badge

        finally:
            fenetre.close()


#
# ==================================================
# Page Étude (§11-§16) — invariants 3 et 4.
# ==================================================
#

class TestEtudeSerie1:

    def test_badge_court(self, qapp, tmp_path):
        """
        §11 / invariant 3 : « Bible : Darby
        révisée · versification : Darby ».
        """

        _p, _pv, _e, _n = (
            construire_etude_test(tmp_path)
        )

        from ui.etude_window import EtudeWindow

        page = EtudeWindow(
            tmp_path / "Etude",
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            badge = (
                page.badge_bible_label.text()
            )

            assert badge == (
                "Bible : Darby révisée "
                "· versification : Darby"
            )

        finally:
            page.close()

    def test_noms_courts_bibles(self):
        """
        Invariant 3 : libellés courts des versions.
        """

        from services.bibles import (
            nom_court_bible,
        )

        assert nom_court_bible("darby") == "Darby"
        assert (
            nom_court_bible("darbyR")
            == "Darby révisée"
        )
        assert (
            nom_court_bible("segond1910")
            == "Segond 1910"
        )

    def test_date_de_reunion_pas_technique(
        self,
        tmp_path
    ):
        """
        §12 / invariant 4 : la date affichée est la
        date de l'AUDIO, jamais la date technique
        de rattachement.
        """

        projet, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        dossier = tmp_path / "2026-10-13_Luc1b"

        # Un audio daté d'un jour connu.
        audio = dossier / "enregistrement.wav"
        audio.write_bytes(b"RIFF....")

        # Date de l'audio : 2024-05-06 (mtime).
        moment = time.mktime(
            time.struct_time(
                (2024, 5, 6, 12, 0, 0, 0, 0, -1)
            )
        )

        os.utime(audio, (moment, moment))

        import json

        chemin_sttproj = (
            dossier / "project.sttproj"
        )

        data = json.loads(
            chemin_sttproj.read_text(
                encoding="utf-8"
            )
        )

        data["audio_file"] = "enregistrement.wav"

        chemin_sttproj.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        from services.avancement import (
            date_reunion,
        )
        from services.project_io import (
            load_project,
        )

        projet_charge = load_project(
            str(chemin_sttproj)
        )

        reunion = etude.reunions[nom]

        # Date technique (rattachement) = aujourd'hui.
        assert reunion.date != "2024-05-06"

        # Date affichée = date de l'audio.
        assert date_reunion(
            projet_charge,
            reunion
        ) == "2024-05-06"

    def test_rattachement_stoke_date_audio(
        self,
        tmp_path
    ):
        """
        La date stockée à l'attachement est la date
        de réunion (audio), pas la date du jour.
        """

        projet, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        dossier = tmp_path / "2026-10-13_Luc1b"

        audio = dossier / "enregistrement.wav"
        audio.write_bytes(b"RIFF....")

        moment = time.mktime(
            time.struct_time(
                (2024, 5, 6, 12, 0, 0, 0, 0, -1)
            )
        )

        os.utime(audio, (moment, moment))

        import json

        chemin_sttproj = (
            dossier / "project.sttproj"
        )

        data = json.loads(
            chemin_sttproj.read_text(
                encoding="utf-8"
            )
        )

        data["audio_file"] = "enregistrement.wav"

        chemin_sttproj.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        from services.etude_io import creer_etude
        from services.rattachement import (
            rattacher,
        )

        creer_etude(
            tmp_path / "AutreEtude",
            "Autre étude"
        )

        # On retire d'abord la réunion de son étude
        # (exclusivité : une réunion ∈ 0 ou 1 étude).
        from services.etude_io import (
            retirer_reunion,
            sauvegarder_etude,
        )

        retirer_reunion(etude, nom)
        sauvegarder_etude(etude)

        nouveau_nom = rattacher(
            tmp_path / "AutreEtude",
            dossier,
            etudes_connues=[]
        )

        recharge = (
            __import__(
                "services.etude_io",
                fromlist=["ouvrir_etude"]
            ).ouvrir_etude(
                tmp_path / "AutreEtude"
            )
        )

        assert (
            recharge.reunions[nouveau_nom].date
            == "2024-05-06"
        )

    def test_titre_tuile_lisible(
        self,
        qapp,
        tmp_path
    ):
        """
        §13 : titre lisible sans numérotation ni
        nom de fichier brut ; rang en information
        annexe.
        """

        _p, _pv, _e, _n = (
            construire_etude_test(tmp_path)
        )

        from ui.etude_window import EtudeWindow

        page = EtudeWindow(
            tmp_path / "Etude",
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            tuiles = (
                page.reunions_liste
                .findChildren(QLabel)
            )

            textes = [
                l.text() for l in tuiles
            ]

            # Titre = titre de réunion lisible.
            assert "Chapitre 1" in textes

            # Pas de numérotation dans le titre.
            assert "1. Chapitre 1" not in textes

            # Rang en information annexe.
            assert "Réunion 1" in textes

        finally:
            page.close()

    def test_entete_reunions_et_ajouter(
        self,
        qapp,
        tmp_path
    ):
        """
        §16 : titre de section « Réunions de
        l'étude », « ＋ Ajouter une réunion » en
        tête de liste, à côté du titre.
        """

        _p, _pv, _e, _n = (
            construire_etude_test(tmp_path)
        )

        from ui.etude_window import EtudeWindow

        page = EtudeWindow(
            tmp_path / "Etude",
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            labels = [
                l.text()
                for l in page.findChildren(QLabel)
            ]

            assert "Réunions de l'étude" in labels

            assert (
                page.ajouter_button.text()
                == "＋ Ajouter une réunion…"
            )

        finally:
            page.close()

    def test_pluriel_reunions(
        self,
        qapp,
        tmp_path
    ):
        """
        §15 : « 2 réunions », jamais « 2 réunion(s) ».
        """

        import shutil

        _p, _pv, _e, _n = (
            construire_etude_test(tmp_path)
        )

        dossier2 = tmp_path / "Autre_reunion"
        shutil.copytree(
            tmp_path / "2026-10-13_Luc1b",
            dossier2
        )

        from services.etude_io import (
            ajouter_reunion,
        )
        from ui.etude_window import EtudeWindow

        etude = __import__(
            "services.etude_io",
            fromlist=["ouvrir_etude"]
        ).ouvrir_etude(tmp_path / "Etude")

        ajouter_reunion(etude, dossier2)

        from services.etude_io import (
            sauvegarder_etude,
        )

        sauvegarder_etude(etude)

        page = EtudeWindow(
            tmp_path / "Etude",
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            assert "2 réunions" in (
                page.sous_titre_label.text()
            )

            assert "réunion(s)" not in (
                page.sous_titre_label.text()
            )

        finally:
            page.close()
