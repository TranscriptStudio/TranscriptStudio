"""
Tests P18.6a — hub d'accueil à 3 tuiles (spec
NAVIGATION_V2_2026-10-29b §2) et fondations :
service d'avancement (stepper ①→⑥), trace
d'export, StepperBar, service de rattachement
(exclusivité — invariant §9.1, option A —
invariant §9.5).
"""

import json
import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
)

from services.avancement import (
    A_FAIRE,
    EN_COURS,
    ETAPES_ETUDE,
    ETAPES_OPTIONNELLES,
    ETAPES_REUNION,
    TERMINE,
    cout_reunion,
    etapes_reunion,
    etapes_reunion_page_etude,
    etat_correction,
    etat_export,
    etat_pretraitement,
    etat_reformulation,
    etat_resume,
    etat_transcription,
)
from services.etude_io import (
    ajouter_version_reformulation,
    ajouter_version_resume,
    valider_version_reformulation,
    valider_version_resume,
)
from services.rattachement import (
    RattachementError,
    changer_etude,
    detacher_reunion,
    rattachement_de,
    rattacher,
    reunions_des_etudes,
    verifier_exclusivite,
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


#
# ==================================================
# Service d'avancement (états du stepper).
# ==================================================
#

class TestAvancement:

    def test_base_projet_v1(self, tmp_path):

        _projet, projet_v1, _etude, _nom = (
            construire_etude_test(tmp_path)
        )

        # Transcription (mots) et correction (blocs
        # de diarisation) sont terminées.
        assert etat_transcription(
            projet_v1
        ) == TERMINE

        assert etat_correction(
            projet_v1
        ) == TERMINE

        # Pas de journal de prétraitement : ① à faire.
        assert etat_pretraitement(
            projet_v1
        ) == A_FAIRE

    def test_pretraitement_avec_journal(
        self,
        tmp_path
    ):

        projet, projet_v1, _e, _n = (
            construire_etude_test(tmp_path)
        )

        dossier = (
            tmp_path / "2026-10-13_Luc1b"
        )

        (dossier / "journal_operations.json").write_text(
            json.dumps({"operations": []}),
            encoding="utf-8"
        )

        # Le journal vit dans le dossier du projet :
        # l'état se lit après rechargement du projet.
        from services.project_io import (
            load_project
        )

        recharge = load_project(
            str(dossier / "project.sttproj")
        )

        assert etat_pretraitement(
            recharge
        ) == TERMINE

    def test_sans_transcription(self, tmp_path):

        dossier = tmp_path / "vide"
        dossier.mkdir()

        (dossier / "project.sttproj").write_text(
            json.dumps({
                "project_format_version": 1,
                "name": "Vide",
                "audio_file": "",
                "transcription_id": None,
                "language_code": "fr",
                "duration_seconds": 0.0,
                "modified": False,
                "speakers": [],
                "words": [],
                "blocks": [],
                "original_elevenlabs_response": {},
            }),
            encoding="utf-8"
        )

        from services.project_io import (
            load_project
        )

        projet = load_project(
            str(dossier / "project.sttproj")
        )

        assert etat_transcription(projet) == A_FAIRE
        assert etat_correction(projet) == A_FAIRE

    def test_reformulation_optionnelle(self, tmp_path):

        _p, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        # Sans résultats : à faire (optionnelle,
        # l'utilisateur peut la passer).
        assert etat_reformulation(
            etude, nom
        ) == A_FAIRE

        fids = [
            entree.fid
            for entree in (
                etude.registre.entrees.values()
            )
            if entree.reunion == nom
        ]

        # Quelques résultats, rien de validé : en cours.
        for fid in fids[:2]:
            ajouter_version_reformulation(
                etude,
                fid,
                "Texte reformulé."
            )

        assert etat_reformulation(
            etude, nom
        ) == EN_COURS

        # Tout validé : terminé.
        for fid in fids:
            ajouter_version_reformulation(
                etude,
                fid,
                "Texte reformulé."
            )

            valider_version_reformulation(
                etude,
                fid,
                etude
                .reformulations[fid]
                .versions[-1]
                .numero,
                validateur="Test"
            )

        assert etat_reformulation(
            etude, nom
        ) == TERMINE

    def test_resume_optionnel(self, tmp_path):

        _p, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        assert etat_resume(etude, nom) == A_FAIRE

        ajouter_version_resume(
            etude,
            nom,
            "Résumé en cours de rédaction.",
            source="brute_corrigee"
        )

        assert etat_resume(etude, nom) == EN_COURS

        valider_version_resume(
            etude,
            nom,
            1,
            validateur="Test"
        )

        assert etat_resume(etude, nom) == TERMINE

    def test_export_trace_reglages(self, tmp_path):

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        chemin = str(
            tmp_path / "reunion.sttproj"
        )

        assert etat_export(
            chemin, settings
        ) == A_FAIRE

        settings.enregistrer_export_reunion(chemin)

        assert etat_export(
            chemin, settings
        ) == TERMINE

        # Le projet v1 n'est jamais touché : la trace
        # vit dans les réglages de l'app.
        assert not (
            tmp_path / "reunion.sttproj"
        ).exists()

    def test_cout_reunion(self, tmp_path):

        _p, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        assert cout_reunion(etude, nom) == 0.0

        fids = [
            entree.fid
            for entree in (
                etude.registre.entrees.values()
            )
            if entree.reunion == nom
        ]

        ajouter_version_reformulation(
            etude,
            fids[0],
            "Texte.",
            stats={"cout_estime": 0.01}
        )

        ajouter_version_resume(
            etude,
            nom,
            "Résumé.",
            source="brute_corrigee",
            stats={"cout_estime": 0.02}
        )

        assert abs(
            cout_reunion(etude, nom) - 0.03
        ) < 1e-9

    def test_etapes_completes_reunion(self, tmp_path):

        _p, projet_v1, etude, nom = (
            construire_etude_test(tmp_path)
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        etats = etapes_reunion(
            projet_v1,
            etude_ouverte=etude,
            nom=nom,
            settings=settings
        )

        # Stepper COMPACT (P18.6-bis §19) :
        # ① Transcription → ② Reformulation →
        # ③ Résumé → ④ Export ; ② et ③
        # optionnelles ; les étapes Prétraitement /
        # Transcription / Correction n'apparaissent
        # plus séparément.
        assert tuple(etats.keys()) == ETAPES_REUNION

        assert ETAPES_REUNION == (
            "transcription",
            "reformulation",
            "resume",
            "export"
        )

        assert ETAPES_OPTIONNELLES == (
            "reformulation",
            "resume"
        )

        # Invariant §9.4 : l'affichage d'avancement
        # de la page Étude ne montre JAMAIS le ⑥.
        assert "export" not in (
            etapes_reunion_page_etude(
                etude,
                nom,
                projet_v1
            )
        )

        assert ETAPES_ETUDE == ETAPES_REUNION[:3]


#
# ==================================================
# StepperBar (couleurs, optionnelles pointillées).
# ==================================================
#

class TestStepperBar:

    def test_quatre_etapes_reunion(self, qapp):
        """
        Stepper compact (P18.6-bis §19, invariant
        complémentaire 5) : Transcription →
        Reformulation → Résumé → Export.
        """

        from ui.stepper import StepperBar

        barre = StepperBar()

        assert len(barre.boutons) == 4

        libelles = [
            bouton.text()
            for bouton in barre.boutons.values()
        ]

        assert libelles == [
            "① Transcription",
            "② Reformulation",
            "③ Résumé",
            "④ Export",
        ]

    def test_trois_etapes_page_etude(self, qapp):
        """
        Page Étude : Transcription → Reformulation →
        Résumé, JAMAIS Export (invariant §9.4).
        """

        from ui.stepper import StepperBar

        barre = StepperBar(etapes=ETAPES_ETUDE)

        assert len(barre.boutons) == 3

        assert "④ Export" not in [
            b.text()
            for b in barre.boutons.values()
        ]

    def test_aucun_contour_pointille(self, qapp):
        """
        P18.6-bis (spec correctifs §18, invariant
        complémentaire 6) : aucune pastille n'a de
        contour pointillé ; l'optionnalité ne se
        lit que dans l'info-bulle.
        """

        from ui.stepper import StepperBar

        barre = StepperBar()

        for etape, bouton in (
            barre.boutons.items()
        ):
            assert "dashed" not in (
                bouton.styleSheet()
            ), etape

        # Optionnalité : info-bulle uniquement.
        assert (
            barre.boutons["reformulation"]
            .toolTip()
            == "Étape optionnelle"
        )

        assert (
            barre.boutons["resume"]
            .toolTip()
            == "Étape optionnelle"
        )

        assert not (
            barre.boutons["export"]
            .toolTip()
        )

    def test_couleurs_etats(self, qapp):

        from services.avancement import (
            EN_COURS,
            TERMINE,
        )
        from ui.stepper import StepperBar

        barre = StepperBar()

        barre.definir_etats({
            "transcription": TERMINE,
            "reformulation": EN_COURS,
        })

        # Série 5 (spec 30f §24) : fait = émeraude
        # translucide, en cours = bleu plein.
        assert "#2ec98a" in (
            barre.boutons["transcription"]
            .styleSheet()
        )

        assert "#2563eb" in (
            barre.boutons["reformulation"]
            .styleSheet()
        )

        assert "#ffffff" in (
            barre.boutons["reformulation"]
            .styleSheet()
        )


#
# ==================================================
# Rattachement : exclusivité (§9.1) et option A (§9.5).
# ==================================================
#

class TestRattachement:

    def test_rattachement_de(self, tmp_path):

        projet, _pv, _e, nom = (
            construire_etude_test(tmp_path)
        )

        trouve = rattachement_de(
            str(projet),
            [tmp_path / "Etude"]
        )

        assert trouve is not None
        assert trouve[0] == str(tmp_path / "Etude")
        assert trouve[1] == nom

        # Une autre réunion est autonome.
        assert rattachement_de(
            str(tmp_path),
            [tmp_path / "Etude"]
        ) is None

    def test_exclusivite_0_ou_1_etude(self, tmp_path):
        """
        Invariant §9.1 : une réunion appartient à
        0 ou 1 étude, à tout instant.
        """

        projet, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        dossier_v1 = str(
            tmp_path / "2026-10-13_Luc1b"
        )

        from services.etude_io import creer_etude

        creer_etude(
            tmp_path / "AutreEtude",
            "Autre étude"
        )

        connues = [
            tmp_path / "Etude",
            tmp_path / "AutreEtude",
        ]

        # Déjà rattachée à « Etude » : conflit pour
        # toute autre étude.
        assert verifier_exclusivite(
            dossier_v1,
            connues
        ) == (
            str(tmp_path / "Etude"),
            nom
        )

        # Une étude qui n'est pas la sienne ne voit
        # pas la réunion : pas de faux conflit.
        assert verifier_exclusivite(
            dossier_v1,
            [tmp_path / "AutreEtude"],
            dossier_exclu=tmp_path / "Etude"
        ) is None

        # Rattachement à une seconde étude : refusé.
        with pytest.raises(RattachementError):
            rattacher(
                tmp_path / "AutreEtude",
                dossier_v1,
                etudes_connues=connues
            )

        # Rien n'a été écrit dans la seconde étude.
        assert reunions_des_etudes(
            tmp_path / "AutreEtude"
        ) == {}

    def test_detacher_garde_les_traitements(self, tmp_path):
        """
        Invariant §9.5 : un changement d'étude ne
        déplace ni ne copie aucun traitement — tout
        reste à l'ancienne étude.
        """

        projet, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        fids = [
            entree.fid
            for entree in (
                etude.registre.entrees.values()
            )
            if entree.reunion == nom
        ]

        ajouter_version_reformulation(
            etude,
            fids[0],
            "Texte validé.",
        )

        valider_version_reformulation(
            etude,
            fids[0],
            1,
            validateur="Test"
        )

        from services.etude_io import (
            sauvegarder_etude
        )

        sauvegarder_etude(etude)

        dossier_etude = tmp_path / "Etude"

        fichier_decoupage = (
            dossier_etude
            / "blocs" / "decoupage"
            / f"{nom}.json"
        )

        fichier_reformulation = (
            dossier_etude
            / "traitements" / "reformulation"
            / f"{fids[0]}.json"
        )

        assert fichier_decoupage.is_file()
        assert fichier_reformulation.is_file()

        detacher_reunion(etude, nom)

        from services.etude_io import sauvegarder_etude

        sauvegarder_etude(etude)

        # La référence a disparu...
        assert not (
            dossier_etude
            / "reunions"
            / f"{nom}.json"
        ).exists()

        assert nom not in etude.etude.ordre_reunions

        # ...les traitements RESTENT (option A).
        assert fichier_decoupage.is_file()
        assert fichier_reformulation.is_file()

    def test_changer_etude_option_a(self, tmp_path):

        projet, _pv, etude, nom = (
            construire_etude_test(tmp_path)
        )

        dossier_v1 = str(
            tmp_path / "2026-10-13_Luc1b"
        )

        fids = [
            entree.fid
            for entree in (
                etude.registre.entrees.values()
            )
            if entree.reunion == nom
        ]

        ajouter_version_reformulation(
            etude,
            fids[0],
            "Texte."
        )

        from services.etude_io import (
            creer_etude,
            sauvegarder_etude,
        )

        sauvegarder_etude(etude)

        creer_etude(
            tmp_path / "AutreEtude",
            "Autre étude"
        )

        nouveau_nom = changer_etude(
            tmp_path / "Etude",
            nom,
            tmp_path / "AutreEtude",
            etudes_connues=[
                tmp_path / "Etude",
                tmp_path / "AutreEtude",
            ]
        )

        # La réunion appartient désormais à la
        # nouvelle étude (0 ou 1, jamais 2).
        assert rattachement_de(
            dossier_v1,
            [
                tmp_path / "Etude",
                tmp_path / "AutreEtude",
            ]
        ) == (
            str(tmp_path / "AutreEtude"),
            nouveau_nom
        )

        # Les traitements restent à l'ancienne étude.
        assert (
            tmp_path / "Etude"
            / "traitements" / "reformulation"
            / f"{fids[0]}.json"
        ).is_file()

        assert not (
            tmp_path / "AutreEtude"
            / "traitements" / "reformulation"
            / f"{fids[0]}.json"
        ).exists()


#
# ==================================================
# Hub (bandeau, tuiles, mini-tuiles).
# ==================================================
#

@pytest.fixture
def catalogue_defaut():

    from services.llm.catalogue import (
        catalogue_par_defaut,
    )

    return catalogue_par_defaut()


class TestHub:

    def test_bandeau_hub_v4(
        self,
        qapp,
        tmp_path,
        catalogue_defaut
    ):
        """
        Hub v4 (spec 30f §25, invariant 12) : pas
        de salutation, pastilles de services sur
        la plaque métal brossé, boutons ⚙/? à une
        seule icône, « Version 2.0 » sous le
        sous-titre.
        """

        from ui.home_window import HomeWindow

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        with patch(
            "services.llm.catalogue.charger_catalogue",
            return_value=catalogue_defaut,
        ):
            accueil = HomeWindow(settings=settings)

        try:
            # Bandeau app : uniquement sur l'accueil
            # (invariant §9.2).
            assert accueil.bandeau.objectName() == (
                "bandeau_app"
            )

            # Invariant 12 : AUCUNE salutation.
            assert not hasattr(
                accueil,
                "salutation_label"
            )

            # Trois GRANDES tuiles, titres exacts.
            tuiles = [
                accueil.tuile_nouvelle.titre,
                accueil.tuile_reprendre.titre,
                accueil.tuile_etudes.titre,
            ]

            assert tuiles == [
                "Nouvelle transcription",
                "Reprendre une réunion",
                "Études",
            ]

            # Plaque métal brossé des services.
            assert accueil.plaque_services                 .objectName() == "plaque_services"

            style = (
                accueil
                .plaque_services
                .styleSheet()
            )

            assert "#2e2f35" in style
            assert "#27282e" in style
            assert "#3c3d44" in style

            # Boutons ⚙/? : une seule icône, pas de
            # texte.
            assert not accueil.settings_button.text()
            assert not accueil.help_button.text()

            assert accueil.settings_button.icon()                 .isNull() is False

            assert accueil.help_button.icon()                 .isNull() is False

            # « Version 2.0 » sous le sous-titre.
            assert (
                accueil.version_label.text()
                == "Version 2.0"
            )

        finally:
            accueil.close()

    def test_mini_tuile_autonome_et_rattachement(
        self,
        qapp,
        tmp_path,
        catalogue_defaut
    ):

        from ui.home_window import HomeWindow

        projet, projet_v1, etude, nom = (
            construire_etude_test(tmp_path)
        )

        # Une réunion AUTONOME dans les récents
        # (hors de toute étude) : mini-tuile avec
        # badge « Réunion autonome » + lien de
        # rattachement (spec §2.4).
        dossier_v1 = (
            tmp_path / "2026-10-13_Luc1b"
        )

        fichier_v1 = (
            dossier_v1 / "project.sttproj"
        )

        from services.etude_io import (
            retirer_reunion,
            sauvegarder_etude,
        )

        retirer_reunion(etude, nom)
        sauvegarder_etude(etude)

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.add_recent_project(
            str(fichier_v1)
        )

        with patch(
            "services.llm.catalogue.charger_catalogue",
            return_value=catalogue_defaut,
        ):
            accueil = HomeWindow(settings=settings)

        try:
            from ui.tuiles import TuileReunion

            tuiles = (
                accueil
                .dernieres_conteneur
                .findChildren(TuileReunion)
            )

            assert tuiles, (
                "la tuile-rangée de la réunion récente "
                "doit exister"
            )

            # Invariant 11 : AUCUN bouton « Ouvrir »
            # sur les tuiles de réunion du hub — le
            # clic sur la tuile ouvre la réunion.
            boutons = [
                b.text()
                for b in (
                    accueil.findChildren(QPushButton)
                )
            ]

            assert "Ouvrir" not in boutons

            libelles = [
                w.text()
                for w in accueil.findChildren(QPushButton)
            ]

            assert (
                "rattacher à une étude…" in libelles
            )

            # Le clic (signal de la tuile) ouvre la
            # réunion.
            ouverts = []

            tuiles[0].ouvrir_demandee.connect(
                ouverts.append
            )

            tuiles[0].mousePressEvent(None)

            assert ouverts == [tuiles[0].chemin]

            # La réunion étant autonome, aucun badge
            # d'étude ne s'affiche.
            from PySide6.QtWidgets import QLabel

            badges = [
                l.text()
                for l in accueil.findChildren(QLabel)
                if l.text().startswith("Étude «")
            ]

            assert badges == []

        finally:
            accueil.close()

    def test_mini_tuile_attachee_stepper_complet(
        self,
        qapp,
        tmp_path,
        catalogue_defaut
    ):

        from ui.home_window import HomeWindow

        projet, projet_v1, etude, nom = (
            construire_etude_test(tmp_path)
        )

        dossier_v1 = (
            tmp_path / "2026-10-13_Luc1b"
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.add_recent_project(
            str(dossier_v1 / "project.sttproj")
        )

        settings.add_recent_etude(
            str(tmp_path / "Etude")
        )

        with patch(
            "services.llm.catalogue.charger_catalogue",
            return_value=catalogue_defaut,
        ):
            accueil = HomeWindow(settings=settings)

        try:
            from PySide6.QtWidgets import QLabel

            etudes_badge = [
                l.text()
                for l in accueil.findChildren(QLabel)
                if l.text().startswith("Étude «")
            ]

            # Rattachée : badge d'étude (présent sur
            # chacune des deux pages empilées de la
            # tuile), pas de lien de rattachement.
            assert len(etudes_badge) >= 1

            from ui.stepper import StepperBar

            steppers = (
                accueil.findChildren(StepperBar)
            )

            assert steppers

            # Stepper COMPACT ①→④ sur le hub, une
            # fois la transcription faite (P18.6-bis
            # §19, invariant complémentaire 5) — la
            # page « une ligne » a le sien.
            assert all(
                len(s.boutons) == 4
                for s in steppers
            )

        finally:
            accueil.close()

    def test_pastille_llm_verte_si_cle(
        self,
        qapp,
        tmp_path,
        catalogue_defaut
    ):

        from services.credential_store import (
            CredentialStore
        )
        from ui.home_window import HomeWindow

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        with patch(
            "services.llm.catalogue.charger_catalogue",
            return_value=catalogue_defaut,
        ):
            accueil = HomeWindow(settings=settings)

        try:
            # Aucune clé : point GRIS (off).
            assert "#8a8b92" in (
                accueil.llm_pastille.styleSheet()
            )

            store = CredentialStore(
                settings.app_folder / "settings.json"
            )

            store.set_cle_llm(
                "openai",
                "sk-test"
            )

            accueil.maj_statut_llm()

            # Clé enregistrée : point VERT (ok).
            assert "#3fa66c" in (
                accueil.llm_pastille.styleSheet()
            )

        finally:
            accueil.close()
