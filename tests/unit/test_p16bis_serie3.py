"""
Tests P16-bis, 3ᵉ série de correctifs de relecture
(spec UI_REFORMULATION_MODIFS_V2_2026-10-27d.md
§15-§18).

Règles d'invariance :
- §15 : quitter la page Reformulation arrête la
  lecture et libère l'audio ; le retour
  réinitialise un lecteur jouable (curseur
  conservé) ; erreur audio signalée ;
- §16 : aucun chemin de clic ne lance la lecture
  — seul le bouton lecture/pause joue ;
- §17 : la clé API LLM survit à un redémarrage
  complet (CredentialStore), champ masqué
  prérempli (parité ElevenLabs) ;
- §18 : l'éditeur de catalogue est strictement
  lié à la sélection (modèles du fournisseur
  courant uniquement, désélection au changement
  de fournisseur, pas de doublons, défauts
  préremplis, repli sur les défauts si fichier
  stocké invalide).
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
    QLineEdit,
)

from services.credential_store import CredentialStore
from services.llm.catalogue import (
    catalogue_par_defaut,
    charger_catalogue,
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


class LecteurFictif:
    """
    Doubure du PlaybackManager : enregistre chaque
    appel (offscreen, aucun média réel).
    """

    def __init__(self):
        self.appels = []

    def load_file(self, chemin):
        self.appels.append(("charge", chemin))

    def set_position(self, position):
        self.appels.append(("position", position))

    def get_position(self):
        return 42.0

    def play(self):
        self.appels.append(("lecture",))

    def pause(self):
        self.appels.append(("pause",))

    def stop(self):
        self.appels.append(("arret",))

    def unload(self):
        self.appels.append(("liberation",))

    def a_joue(self) -> bool:
        return any(
            appel[0] == "lecture"
            for appel in self.appels
        )


@pytest.fixture
def fenetre(qapp, tmp_path):
    """
    Page Reformulation d'une étude test, lecteur
    remplacé par une doubure enregistrante.
    """

    _projet, _projet_v1, _etude, nom = (
        construire_etude_test(tmp_path)
    )

    from services.etude_io import ouvrir_etude

    from ui.reformulation_window import (
        ReformulationWindow
    )

    etude_disco = ouvrir_etude(tmp_path / "Etude")

    fenetre = ReformulationWindow(
        etude_disco,
        nom,
        settings=SettingsManager(
            str(tmp_path / "reglages")
        )
    )

    fenetre.playback = LecteurFictif()

    yield fenetre

    fenetre.close()


@pytest.fixture
def app(qapp, tmp_path):
    """
    Fenêtre principale à pile unique + une étude.
    """

    from ui.app_window import AppWindow

    projet, projet_v1, etude, nom = (
        construire_etude_test(tmp_path)
    )

    settings = SettingsManager(
        str(tmp_path / "reglages")
    )

    settings.add_recent_etude(
        str(tmp_path / "Etude")
    )

    fenetre_app = AppWindow(settings=settings)

    yield fenetre_app, projet, projet_v1, etude, nom

    fenetre_app.close()


#
# ==================================================
# §15 — lecteur audio sain au retour de page.
# ==================================================
#

@pytest.mark.qt
class TestSection15Lecteur:

    def test_quitter_arrete_et_libere(self, fenetre):

        fenetre.sur_navigation_sortante()

        appels = fenetre.playback.appels

        assert ("arret",) in appels
        assert ("liberation",) in appels

        # Pas de son orphelin : le lecteur ne joue
        # pas en arrière-plan.
        assert not fenetre.playback.a_joue()

    def test_position_conservee_puis_restaurée(self, fenetre, tmp_path):

        audio = tmp_path / "reunion.wav"
        audio.write_bytes(b"RIFF....")

        fenetre.projet_v1.audio_file = str(audio)

        fenetre.sur_navigation_sortante()

        # La dernière position est conservée.
        assert fenetre.derniere_position == 42.0

        fenetre.sur_navigation_entrante()

        appels = fenetre.playback.appels

        # Retour : lecteur rechargé, curseur
        # restauré — jouable immédiatement, sans
        # lecture automatique.
        assert ("charge", str(audio)) in appels
        assert ("position", 42.0) in appels

        assert not fenetre.playback.a_joue()

    def test_erreur_audio_signalee(self, fenetre):

        fenetre.sur_erreur_audio("périphérique absent")

        assert "périphérique absent" in (
            fenetre.barre_etat.text()
        )

        assert (
            fenetre.jouer_button.text() == "▶ Audio"
        )

    def test_pile_appelle_entrante_au_retour(self, app, tmp_path):

        fenetre_app, projet, projet_v1, etude, nom = app

        from services.etude_io import ouvrir_etude

        etude_ouverte = ouvrir_etude(
            tmp_path / "Etude"
        )

        ref = fenetre_app.ouvrir_reformulation(
            etude_ouverte,
            nom
        )

        fenetre_app.ouvrir_etude(tmp_path / "Etude")

        with patch.object(
            ref,
            "sur_navigation_entrante"
        ) as entrante:

            fenetre_app.ouvrir_reformulation(
                etude_ouverte,
                nom
            )

            assert entrante.called

        # La page est réactivée, pas dupliquée.
        assert fenetre_app.page_active() is ref


#
# ==================================================
# §16 — aucune lecture automatique au clic.
# ==================================================
#

@pytest.mark.qt
class TestSection16PasDeLectureAuto:

    def test_aucun_chemin_de_clic_ne_joue(self, fenetre):

        # Clic dans un bloc (brute).
        fenetre.positionner_audio(
            fenetre.lignes[1],
            0
        )

        # Clic sur la timeline.
        fenetre.sur_clic_timeline(21.0)

        # Clic sur un bloc de la timeline v1.
        fenetre.sur_bloc_timeline_clic(1)

        QApplication.processEvents()

        assert not fenetre.playback.a_joue()

        assert (
            fenetre.jouer_button.text() == "▶ Audio"
        )

        # Le clic timeline a bien sélectionné le
        # bloc courant — sans déclencher l'audio.
        assert fenetre.bloc_courant == 3

    def test_seul_le_bouton_bascule(self, fenetre):

        fenetre.basculer_lecture()

        assert fenetre.playback.a_joue()

        assert (
            fenetre.jouer_button.text() == "⏸ Pause"
        )


#
# ==================================================
# §17 — clé API LLM persistée, parité ElevenLabs.
# ==================================================
#

@pytest.mark.qt
class TestSection17CleLLM:

    def test_cle_survit_au_redemarrage(self, tmp_path):

        fichier = tmp_path / "settings.json"

        store = CredentialStore(fichier)

        store.set_cle_llm("openai", "sk-test-123456")

        # « Redémarrage » : nouveau store, même
        # dossier — la clé est rechargée.
        store2 = CredentialStore(fichier)

        assert store2.get_cle_llm("openai") == (
            "sk-test-123456"
        )

        assert store2.has_cle_llm("openai")

    def test_cle_survit_aux_sauvegardes_des_reglages(self, tmp_path):
        """
        Régression constatée en relecture : la clé
        était EFFACÉE par SettingsManager.save()
        (réécriture entière de settings.json, qui ne
        connaît pas les clés llm_cle_*). Les
        credentials vivent désormais dans leur
        propre fichier — une sauvegarde de réglages
        (thème, récents…) ne peut plus les effacer.
        """

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.save()

        store = CredentialStore(
            settings.app_folder / "settings.json"
        )

        store.set_cle_llm("openai", "sk-test-123456")

        # Toutes les causes d'effacement passées :
        # sauvegarde du thème, projet/étude récent,
        # configuration LLM.
        settings.set_theme("dark")

        settings.add_recent_project(
            str(tmp_path / "reunion.sttproj")
        )

        settings.set_llm_config(
            settings.get_llm_config()
        )

        store2 = CredentialStore(
            settings.app_folder / "settings.json"
        )

        assert store2.get_cle_llm("openai") == (
            "sk-test-123456"
        )

    def test_saisie_puis_reouverture(self, qapp, tmp_path):
        """
        Scénario complet de la relecture : clé
        renseignée et testée dans les réglages,
        enregistrement, réouverture des réglages —
        la clé est toujours là (champ masqué
        prérempli), sans ressaisie.
        """

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.save()

        store = CredentialStore(
            settings.app_folder / "settings.json"
        )

        store.set_cle_llm("openai", "sk-test-123456")

        from ui.settings_dialog import SettingsDialog

        dialogue = SettingsDialog(
            settings=settings
        )

        try:

            # Fournisseur par défaut : openai — le
            # champ est prérempli avec la clé.
            assert (
                dialogue.llm_fournisseur_combo
                .currentData()
                == "openai"
            )

            assert dialogue.llm_cle_edit.text() == (
                "sk-test-123456"
            )

            # « Enregistrer » : la clé persiste malgré
            # les sauvegardes de réglages.
            dialogue.save_settings()

        finally:
            dialogue.close()

        store2 = CredentialStore(
            settings.app_folder / "settings.json"
        )

        assert store2.get_cle_llm("openai") == (
            "sk-test-123456"
        )

        # Réouverture des réglages : clé toujours
        # présente, sans ressaisie.
        dialogue2 = SettingsDialog(
            settings=settings
        )

        try:

            assert dialogue2.llm_cle_edit.text() == (
                "sk-test-123456"
            )

        finally:
            dialogue2.close()

    def test_vider_le_champ_efface(self, tmp_path):

        fichier = tmp_path / "settings.json"

        store = CredentialStore(fichier)

        store.set_cle_llm("openai", "sk-test-123456")

        store.set_cle_llm("openai", "")

        store2 = CredentialStore(fichier)

        assert not store2.has_cle_llm("openai")

    def test_champ_masque_preplini(self, qapp, tmp_path):

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.save()

        store = CredentialStore(
            settings.app_folder / "settings.json"
        )

        store.set_cle_llm("openai", "sk-test-123456")

        from ui.settings_dialog import SettingsDialog

        dialogue = SettingsDialog(
            settings=settings
        )

        dialogue.close()

        # Le champ est prérempli avec la clé
        # persistée (masquée) : le test de
        # connexion fonctionne sans ressaisie.
        assert dialogue.llm_cle_edit.text() == (
            "sk-test-123456"
        )

        assert (
            dialogue.llm_cle_edit.echoMode()
            == QLineEdit.EchoMode.Password
        )


#
# ==================================================
# §18 — éditeur de catalogue lié à la sélection.
# ==================================================
#

@pytest.fixture
def dialogue(qapp):
    """
    Éditeur de catalogue sur les défauts embarqués
    (jamais le fichier réel de paramétrage).
    """

    from ui.catalogue_llm_dialog import (
        CatalogueLLMDialog
    )

    fenetre = CatalogueLLMDialog(
        catalogue=catalogue_par_defaut()
    )

    yield fenetre

    fenetre.close()


def ids_de_la_liste(fenetre):
    return [
        fenetre.liste_modeles.item(i).data(0x0100)
        for i in range(fenetre.liste_modeles.count())
    ]


@pytest.mark.qt
class TestSection18Catalogue:

    def test_chaque_fournisseur_n_affiche_que_ses_modeles(self, dialogue):

        catalogue = dialogue.catalogue

        for i in range(
            dialogue.liste_fournisseurs.count()
        ):
            dialogue.liste_fournisseurs.setCurrentRow(
                i
            )

            attendus = [
                modele.id
                for modele
                in catalogue.fournisseurs[i].modeles
            ]

            assert sorted(ids_de_la_liste(dialogue)) == (
                sorted(attendus)
            )

    def test_changement_de_fournisseur_deselectionne(self, dialogue):

        dialogue.liste_fournisseurs.setCurrentRow(0)

        dialogue.liste_modeles.setCurrentRow(0)

        assert dialogue.modele_id_edit.text() == (
            "gpt-6-astra"
        )

        # Changement de fournisseur : la liste est
        # rechargée, AUCUN modèle sélectionné,
        # panneau à l'état par défaut.
        dialogue.liste_fournisseurs.setCurrentRow(1)

        assert (
            dialogue.liste_modeles.currentRow()
            == -1
        )

        assert dialogue.modele_id_edit.text() == ""

        assert dialogue.modele_courant is None

    def test_panneau_reflete_le_modele_choisi(self, dialogue):

        dialogue.liste_fournisseurs.setCurrentRow(1)

        dialogue.liste_modeles.setCurrentRow(0)

        assert dialogue.modele_id_edit.text() == (
            "mistral-large-latest"
        )

        # Le panneau montre le modèle du
        # fournisseur courant — jamais un autre.
        assert (
            dialogue.fournisseur_courant.id
            == "mistral"
        )

    def test_pas_de_doublons_dans_les_listes(self, dialogue):

        for i in range(
            dialogue.liste_fournisseurs.count()
        ):

            dialogue.liste_fournisseurs.setCurrentRow(
                i
            )

            ids = ids_de_la_liste(dialogue)

            assert len(ids) == len(set(ids))

    def test_defauts_premlis_et_non_corrompus(self, dialogue):
        """
        Après un parcours complet de l'éditeur
        (sélection de fournisseurs et de modèles),
        les fournisseurs par défaut conservent Base
        URL, prix et contexte — aucune écriture
        transitoire (la cause des mélanges
        constatés).
        """

        dialogue.liste_fournisseurs.setCurrentRow(0)

        dialogue.liste_modeles.setCurrentRow(0)

        dialogue.liste_fournisseurs.setCurrentRow(1)

        dialogue.liste_modeles.setCurrentRow(0)

        dialogue.liste_fournisseurs.setCurrentRow(2)

        openai = dialogue.catalogue.chercher_fournisseur(
            "openai"
        )

        assert openai.base_url == (
            "https://api.openai.com/v1"
        )

        astra = openai.chercher_modele("gpt-6-astra")

        assert astra.prix["in_par_million"] == 10.0
        assert astra.prix["out_par_million"] == 50.0

        assert astra.capacites.get(
            "max_contexte_tokens"
        ) == 1050000

        mistral = (
            dialogue.catalogue.chercher_fournisseur(
                "mistral"
            )
        )

        assert mistral.base_url == (
            "https://api.mistral.ai/v1"
        )

        assert mistral.chercher_modele(
            "mistral-large-latest"
        ).nom_affiche == "Mistral Large (dernier)"

    def test_doublon_d_identifiant_refuse(self, dialogue):

        dialogue.liste_fournisseurs.setCurrentRow(0)

        dialogue.liste_modeles.setCurrentRow(0)

        # gpt-4.1 existe déjà chez OpenAI.
        with patch(
            "ui.catalogue_llm_dialog.QMessageBox"
            ".warning"
        ) as avertissement:

            dialogue.modele_id_edit.setText(
                "gpt-4.1"
            )

            assert avertissement.called

        # L'identifiant est refusé : le champ revient
        # à l'identifiant précédent du modèle.
        assert dialogue.modele_id_edit.text() == (
            "gpt-6-astra"
        )

        # Aucun doublon créé dans le fournisseur.
        assert (
            dialogue.fournisseur_courant
            .chercher_modele("gpt-4.1")
            .id == "gpt-4.1"
        )

    def test_fichier_stocke_invalide_repli_defauts(self, tmp_path):
        """
        Un catalogue stocké corrompu (doublons issus
        d'une version antérieure) ne bloque pas
        l'app : repli sur le catalogue embarqué.
        """

        fournisseur = {
            "id": "openai",
            "famille_api": "openai_compatible",
            "base_url": "https://api.openai.com/v1",
            "modeles": [
                {
                    "id": "modele-a",
                    "nom_affiche": "A",
                    "prix": {"in_par_million": 1.0,
                             "out_par_million": 2.0},
                },
                {
                    "id": "modele-a",
                    "nom_affiche": "A (doublon)",
                    "prix": {"in_par_million": 1.0,
                             "out_par_million": 2.0},
                },
            ],
        }

        chemin = tmp_path / "catalogue.json"

        chemin.write_text(
            json.dumps({
                "catalogue_version": 99,
                "fournisseurs": [fournisseur],
            }, ensure_ascii=False),
            encoding="utf-8"
        )

        catalogue = charger_catalogue(chemin)

        # Repli : les défauts embarqués.
        assert (
            catalogue.catalogue_version
            == catalogue_par_defaut()
            .catalogue_version
        )

        assert any(
            f.id == "mistral"
            for f in catalogue.fournisseurs
        )


#
# ==================================================
# Retour relecture complémentaire : statut de test
# conservé par fournisseur + accueil.
# ==================================================
#

@pytest.mark.qt
class TestRetourRelectureStatutEtAccueil:

    def test_statut_test_conserve_par_fournisseur(self, qapp, tmp_path):

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.save()

        store = CredentialStore(
            settings.app_folder / "settings.json"
        )

        store.set_cle_llm("openai", "sk-test-123456")

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from ui.settings_dialog import SettingsDialog

        with patch(
            "ui.settings_dialog.charger_catalogue",
            return_value=catalogue_par_defaut(),
        ):

            dialogue = SettingsDialog(
                settings=settings
            )

        try:

            assert (
                dialogue.llm_fournisseur_combo
                .currentData()
                == "openai"
            )

            # Test réussi (même chemin d'écriture que
            # « Tester la clé », sans réseau).
            dialogue._enregistrer_statut_test(
                "Clé valide. 136 modèle(s) "
                "accessible(s) chez OpenAI.",
                "#2E7D32",
            )

            # Changement de fournisseur : statut
            # neutre pour le nouveau.
            index = (
                dialogue.llm_fournisseur_combo
                .findData("mistral")
            )

            dialogue.llm_fournisseur_combo.setCurrentIndex(
                index
            )

            assert dialogue.llm_test_statut.text() == (
                "Non testée."
            )

            # Retour au fournisseur testé : le
            # résultat du test est conservé (texte
            # et couleur).
            index = (
                dialogue.llm_fournisseur_combo
                .findData("openai")
            )

            dialogue.llm_fournisseur_combo.setCurrentIndex(
                index
            )

            assert "Clé valide" in (
                dialogue.llm_test_statut.text()
            )

            assert "#2E7D32" in (
                dialogue.llm_test_statut.styleSheet()
            )

        finally:
            dialogue.close()

    def test_accueil_affiche_le_service_de_reformulation(self, qapp, tmp_path):

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from ui.home_window import HomeWindow

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.save()

        with patch(
            "services.llm.catalogue.charger_catalogue",
            return_value=catalogue_par_defaut(),
        ):

            accueil = HomeWindow(settings=settings)

        try:

            # Aucune clé : non configuré.
            assert accueil.llm_status_label.text() == (
                "Service de reformulation : "
                "non configuré"
            )

            store = CredentialStore(
                settings.app_folder / "settings.json"
            )

            store.set_cle_llm("openai", "sk-test-123456")

            with patch(
                "services.llm.catalogue.charger_catalogue",
                return_value=catalogue_par_defaut(),
            ):

                accueil.maj_statut_llm()

            texte = accueil.llm_status_label.text()

            assert "configuré —" in texte
            assert "OpenAI" in texte

        finally:
            accueil.close()


@pytest.mark.qt
class TestStatutTestPersistant:

    def test_statut_survit_a_la_reouverture(self, qapp, tmp_path):
        """
        Scénario de relecture : clé testée dans les
        réglages, fermeture, réouverture des
        réglages — le résultat du test est toujours
        affiché.
        """

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.save()

        store = CredentialStore(
            settings.app_folder / "settings.json"
        )

        store.set_cle_llm("openai", "sk-test-123456")

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from ui.settings_dialog import SettingsDialog

        with patch(
            "ui.settings_dialog.charger_catalogue",
            return_value=catalogue_par_defaut(),
        ):

            dialogue = SettingsDialog(
                settings=settings
            )

        try:

            dialogue._enregistrer_statut_test(
                "Clé valide. 136 modèle(s) "
                "accessible(s) chez OpenAI.",
                "#2E7D32",
            )

        finally:
            dialogue.close()

        # Réouverture : statut restauré depuis le
        # CredentialStore.
        with patch(
            "ui.settings_dialog.charger_catalogue",
            return_value=catalogue_par_defaut(),
        ):

            dialogue2 = SettingsDialog(
                settings=settings
            )

        try:

            assert "Clé valide" in (
                dialogue2.llm_test_statut.text()
            )

            assert "#2E7D32" in (
                dialogue2.llm_test_statut.styleSheet()
            )

        finally:
            dialogue2.close()

    def test_invalidation_par_changement_de_cle(self, tmp_path):
        """
        Le statut persisté concernait une clé : si
        la clé change, il est invalidé ; la même clé
        réenregistrée (aller-retour de fournisseur)
        le conserve.
        """

        fichier = tmp_path / "settings.json"

        store = CredentialStore(fichier)

        store.set_cle_llm("openai", "sk-ancienne")

        store.set_statut_test(
            "openai",
            "Clé valide.",
            "#2E7D32",
        )

        # Même valeur : conservé.
        store.set_cle_llm("openai", "sk-ancienne")

        store2 = CredentialStore(fichier)

        assert store2.get_statut_test("openai") == {
            "texte": "Clé valide.",
            "couleur": "#2E7D32",
        }

        # Clé changée : statut invalidé, clé
        # remplacée.
        store.set_cle_llm("openai", "sk-nouvelle")

        store3 = CredentialStore(fichier)

        assert store3.get_statut_test("openai") is (
            None
        )

        assert store3.get_cle_llm("openai") == (
            "sk-nouvelle"
        )


class TestSectionEffortRaisonnement:
    """
    Effort de raisonnement (retour David 2026-10-29)
    : la valeur mémorisée est RESTAURÉE à
    l'ouverture des réglages (le combo repassait
    à sa première entrée, et « Enregistrer »
    écrasait l'ancienne valeur) ; les niveaux
    complets sont exposés (jusqu'à « Très élevé »)
    ; « Défaut de l'API » n'envoie rien.
    """

    def test_effort_memorise_puis_restaure(
        self, qapp, tmp_path
    ):

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.save()

        config = settings.get_llm_config()

        config["fournisseur"] = "openai"
        config["modele"] = "gpt-5.6-terra"
        config["effort_raisonnement"] = "high"

        settings.set_llm_config(config)

        from ui.settings_dialog import SettingsDialog

        dialogue = SettingsDialog(
            settings=settings
        )

        dialogue.show()

        # Onglet LLM : les réglages du modèle y
        # vivent (l'effort n'est visible que sur
        # l'onglet actif).
        onglet_llm = next(
            i for i in range(dialogue.tabs.count())
            if "LLM" in dialogue.tabs.tabText(i)
        )

        dialogue.tabs.setCurrentIndex(onglet_llm)

        try:

            # Le modèle déclare l'effort : la ligne
            # est visible et la valeur mémorisée
            # sélectionnée (pas « Faible » par
            # défaut).
            assert dialogue.llm_effort_ligne.isVisible()

            assert dialogue.llm_effort_combo.currentData() == "high"

            # Enregistrer sans toucher préserve
            # la valeur.
            dialogue.save_settings()

        finally:
            dialogue.close()

        assert settings.get_llm_config().get(
            "effort_raisonnement"
        ) == "high"

        # Réouverture : toujours restaurée.
        dialogue2 = SettingsDialog(
            settings=settings
        )

        try:

            assert dialogue2.llm_effort_combo.currentData() == "high"

        finally:
            dialogue2.close()

    def test_niveaux_complets_exposes(
        self, qapp, tmp_path
    ):

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.save()

        config = settings.get_llm_config()

        config["fournisseur"] = "openai"
        config["modele"] = "gpt-5.6-terra"
        config["effort_raisonnement"] = "xhigh"

        settings.set_llm_config(config)

        from ui.settings_dialog import SettingsDialog

        dialogue = SettingsDialog(
            settings=settings
        )

        try:

            libelles = [
                dialogue.llm_effort_combo.itemText(i)
                for i in range(
                    dialogue.llm_effort_combo.count()
                )
            ]

            assert "Très élevé" in libelles
            assert "Minimal" in libelles

            # « Défaut de l'API » = première entrée,
            # valeur None (jamais de reasoning_effort
            # envoyé).
            assert dialogue.llm_effort_combo.itemData(0) is None

            # Valeur mémorisée inconnue du catalogue :
            # jamais perdue.
            assert dialogue.llm_effort_combo.currentData() == "xhigh"

        finally:
            dialogue.close()
