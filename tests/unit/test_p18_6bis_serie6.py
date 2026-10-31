"""
Tests P18.6-bis, SÉRIE 6 — SPEC_NAVIGATION_
MODIFS_V2_2026-10-31a.md (arbitrages de David du
31/10) :

- §28 : un service NON CONFIGURÉ affiche
  toujours le point GRIS OFF (ElevenLabs comme
  Service IA) — le ROUGE est réservé à un échec
  RÉEL de service (erreur de connexion, clé
  refusée), jamais à une simple absence de
  configuration ;
- §29 : le hub n'affiche NI stepper NI MENTION
  pour une réunion non transcrite (la page
  Étude conserve sa mention discrète).

Invariants complémentaires 14 et 15 de la spec.
"""

import os
from unittest.mock import patch

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
)

from services.settings import SettingsManager
from tests.unit.test_p18_6bis_s3 import (
    ecrire_projet_sans_transcription,
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


#
# ==================================================
# Invariant 14 : non configuré = gris off,
# rouge = échec réel uniquement.
# ==================================================
#

class TestInvariant14Pastilles:

    @pytest.fixture
    def hub(self, qapp, tmp_path):
        """
        Hub aux réglages isolés (jamais la
        configuration réelle de l'utilisateur).
        """

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from ui.home_window import HomeWindow

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        with patch(
            "services.llm.catalogue"
            ".charger_catalogue",
            return_value=catalogue_par_defaut(),
        ):
            accueil = HomeWindow(settings=settings)

        yield accueil

        accueil.close()

    def test_elevenlabs_non_configuree_grise(
        self,
        hub
    ):
        """
        ElevenLabs sans clé : point GRIS OFF —
        plus JAMAIS de rouge pour une simple
        absence de configuration (§28, modifie
        §25a et lève l'écart soumis par le CLI).
        """

        with patch(
            "ui.home_window"
            ".has_transcription_api",
            return_value=False,
        ):
            hub.update_api_status()

        style = hub.api_pastille.styleSheet()

        assert "#8a8b92" in style

        # Le rouge a disparu du cas « non
        # configuré ».
        assert "#c0533f" not in style

        assert hub.ligne_api.toolTip() == (
            "clé API ElevenLabs non configurée"
        )

    def test_elevenlabs_configuree_verte(
        self,
        hub
    ):
        """
        Clé présente : point VERT (inchangé).
        """

        with patch(
            "ui.home_window"
            ".has_transcription_api",
            return_value=True,
        ):
            hub.update_api_status()

        assert "#3fa66c" in (
            hub.api_pastille.styleSheet()
        )

    def test_ia_non_configuree_grise(
        self,
        hub
    ):
        """
        Service IA sans clé : point GRIS OFF —
        même règle pour les deux services (§28).
        """

        hub.maj_statut_llm()

        assert "#8a8b92" in (
            hub.llm_pastille.styleSheet()
        )

        assert "#c0533f" not in (
            hub.llm_pastille.styleSheet()
        )

    def test_aucune_pastille_rouge_sur_le_hub(
        self,
        hub
    ):
        """
        Les DEUX services non configurés : aucun
        point rouge sur la plaque (invariant 14).
        """

        with patch(
            "ui.home_window"
            ".has_transcription_api",
            return_value=False,
        ):
            hub.update_api_status()

        hub.maj_statut_llm()

        styles = (
            hub.api_pastille.styleSheet()
            + hub.llm_pastille.styleSheet()
        )

        assert "c0533f" not in styles
        assert "#b35900" not in styles


#
# ==================================================
# Invariant 15 : réunion non transcrite —
# ni stepper ni mention sur le hub ; la page
# Étude garde sa mention discrète.
# ==================================================
#

class TestInvariant15NonTranscrite:

    def test_hub_sans_stepper_ni_mention(
        self,
        qapp,
        tmp_path
    ):
        """
        Sur le hub, une réunion non transcrite
        n'affiche NI stepper NI mention (§29) —
        la tuile ne montre que le titre et le
        coût.
        """

        chemin = ecrire_projet_sans_transcription(
            tmp_path / "Audio_prepare"
        )

        settings = SettingsManager(
            str(tmp_path / "reglages")
        )

        settings.add_recent_project(str(chemin))

        from services.llm.catalogue import (
            catalogue_par_defaut,
        )
        from ui.home_window import HomeWindow

        with patch(
            "services.llm.catalogue"
            ".charger_catalogue",
            return_value=catalogue_par_defaut(),
        ):
            accueil = HomeWindow(settings=settings)

        try:

            from ui.stepper import StepperBar
            from ui.tuiles import TuileReunion

            tuiles = (
                accueil.findChildren(TuileReunion)
            )

            assert tuiles

            assert not (
                accueil
                .dernieres_conteneur
                .findChildren(StepperBar)
            )

            mentions = [
                l.text()
                for l in (
                    accueil.findChildren(QLabel)
                )
                if l.text()
                == "transcription en attente"
            ]

            assert mentions == []

        finally:
            accueil.close()

    def test_etude_conserve_sa_mention(
        self,
        qapp,
        tmp_path
    ):
        """
        La page Étude CONSERVE sa mention discrète
        pour une réunion non transcrite (§29 —
        inchangé).
        """

        from services.etude_io import (
            ajouter_reunion,
            sauvegarder_etude,
        )

        construire_etude_test(tmp_path)

        chemin = ecrire_projet_sans_transcription(
            tmp_path / "Audio_prepare"
        )

        etude = None

        from services.etude_io import ouvrir_etude

        etude = ouvrir_etude(
            tmp_path / "Etude"
        )

        ajouter_reunion(
            etude,
            tmp_path / "Audio_prepare",
            titre_1="Audio préparé"
        )

        sauvegarder_etude(etude)

        from ui.etude_window import EtudeWindow

        page = EtudeWindow(
            tmp_path / "Etude",
            settings=SettingsManager(
                str(tmp_path / "reglages")
            )
        )

        try:

            mentions = [
                l.text()
                for l in (
                    page.reunions_liste
                    .findChildren(QLabel)
                )
                if l.text()
                == "transcription en attente"
            ]

            assert mentions

        finally:
            page.close()
