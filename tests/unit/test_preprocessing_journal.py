"""
Tests unitaires du journal des opérations de
prétraitement (P14.2) et des conversions position
traitée <-> originale.

Contrat : CONTRAT_FORMAT_ETUDE_V2.md §11, règles de
composition de FEUILLE_DE_ROUTE_V2.md §3.1 :
- l'accélération s'applique aux positions
  post-suppression ;
- les silences supprimés ne sont pas accélérés ;
- les durées originales des silences restent
  exprimées dans le référentiel du discours original.
"""

import json
import wave
from pathlib import Path

import pytest

from models.audio_processing_settings import (
    AudioProcessingSettings
)
from services.audio_processing_pipeline import (
    AudioProcessingPipeline
)
from services.preprocessing_journal import (
    FICHIER_JOURNAL,
    JournalError,
    JournalOperations,
    ajouter_acceleration,
    ajouter_decoupe,
    ajouter_silence_supprime,
    charger_journal,
    duree_originale_pause,
    enregistrer_journal,
    position_originale_vers_traitee,
    position_traitee_vers_originale,
)


from services.timecodes import lire_timecode


def journal_decoupe_seule():
    journal = JournalOperations(
        horodatage="2026-10-13T20:00:00"
    )
    ajouter_decoupe(journal, 60.0, 300.0)
    return journal


def journal_silences_seuls():
    journal = JournalOperations(
        horodatage="2026-10-13T20:00:00"
    )
    ajouter_silence_supprime(
        journal,
        position=100.0,
        duree_originale=4.0,
        buffer=0.2
    )
    return journal


def journal_complet():
    """
    Découpe [30, 900], silences en 100 (5 s,
    buffer 0,25) et 500 (3 s, buffer 0,5),
    accélération x1,25.
    """
    journal = JournalOperations(
        horodatage="2026-10-13T20:00:00"
    )
    ajouter_decoupe(journal, 30.0, 900.0)
    ajouter_silence_supprime(
        journal,
        position=100.0,
        duree_originale=5.0,
        buffer=0.25
    )
    ajouter_silence_supprime(
        journal,
        position=500.0,
        duree_originale=3.0,
        buffer=0.5
    )
    ajouter_acceleration(journal, 1.25)
    return journal


class TestSerialisation:

    def test_round_trip_dict(self):
        journal = journal_complet()

        relu = JournalOperations.from_dict(
            journal.to_dict()
        )

        assert relu.to_dict() == journal.to_dict()

        # Format timecode du contrat (§11).
        operation_silence = relu.operations[1]

        assert operation_silence["type"] == (
            "silence_supprime"
        )
        assert operation_silence["position"] == (
            "00:01:40.000"
        )
        assert operation_silence[
            "duree_originale"
        ] == "00:00:05.000"

        operation_decoupe = relu.operations[0]

        assert operation_decoupe["positions"] == [
            "00:00:30.000",
            "00:15:00.000",
        ]

    def test_fichier_remplace_l_ancien(self, tmp_path):
        journal = journal_decoupe_seule()
        chemin = enregistrer_journal(journal, tmp_path)

        assert chemin.name == FICHIER_JOURNAL

        # Un nouveau journal remplace l'ancien.
        enregistrer_journal(
            journal_silences_seuls(),
            tmp_path
        )

        relu = charger_journal(tmp_path)

        assert len(relu.operations) == 1
        assert relu.operations[0]["type"] == (
            "silence_supprime"
        )

    def test_chargement_absent(self, tmp_path):
        assert charger_journal(tmp_path) is None

    def test_validation_type_inconnu(self, tmp_path):
        chemin = tmp_path / FICHIER_JOURNAL
        chemin.write_text(
            json.dumps({
                "journal_version": 1,
                "horodatage": "2026-10-13T20:00:00",
                "operations": [
                    {"type": "reverberation"}
                ],
            }),
            encoding="utf-8"
        )

        with pytest.raises(JournalError):
            charger_journal(tmp_path)

    def test_validation_buffer_trop_grand(self):
        journal = JournalOperations()
        ajouter_silence_supprime(
            journal,
            position=10.0,
            duree_originale=1.0,
            buffer=0.6
        )

        with pytest.raises(JournalError):
            JournalOperations.from_dict(journal.to_dict())

    def test_validation_facteur_invalide(self):
        journal = JournalOperations()
        ajouter_acceleration(journal, 0.8)

        with pytest.raises(JournalError):
            JournalOperations.from_dict(journal.to_dict())

    def test_validation_decoupe_mal_formee(self):
        journal = JournalOperations()
        ajouter_decoupe(journal, 0.0, 60.0)
        journal.operations[0]["positions"] = ["seule"]

        with pytest.raises(JournalError):
            JournalOperations.from_dict(journal.to_dict())


class TestConversions:

    def test_journal_vide_identite(self):
        journal = JournalOperations()

        for position in (0.0, 12.5, 300.0):
            assert (
                position_originale_vers_traitee(
                    journal,
                    position
                )
                == position
            )
            assert (
                position_traitee_vers_originale(
                    journal,
                    position
                )
                == position
            )

    def test_decoupe_seule(self):
        journal = journal_decoupe_seule()

        # Avant la découpe : 0.
        assert (
            position_originale_vers_traitee(
                journal,
                50.0
            )
            == 0.0
        )

        # Après le début : décalée de t0.
        assert (
            position_originale_vers_traitee(
                journal,
                100.0
            )
            == pytest.approx(40.0)
        )

        # Après la fin conservée : clampée à la fin.
        assert (
            position_originale_vers_traitee(
                journal,
                350.0
            )
            == pytest.approx(240.0)
        )

        # Retour.
        assert (
            position_traitee_vers_originale(
                journal,
                40.0
            )
            == pytest.approx(100.0)
        )

    def test_silences_seuls(self):
        journal = journal_silences_seuls()

        # Avant le silence : inchangée.
        assert (
            position_originale_vers_traitee(
                journal,
                50.0
            )
            == pytest.approx(50.0)
        )

        # Après le silence : décalée de la partie
        # supprimée (4 - 2*0.2 = 3.6 s).
        assert (
            position_originale_vers_traitee(
                journal,
                200.0
            )
            == pytest.approx(196.4)
        )

        # Dans la partie supprimée : projetée sur le
        # début de la coupe (fin de l'audio conservé).
        assert (
            position_originale_vers_traitee(
                journal,
                102.0
            )
            == pytest.approx(100.2)
        )

        # Frontière exacte : conservatrice.
        assert (
            position_traitee_vers_originale(
                journal,
                100.2
            )
            == pytest.approx(100.2)
        )

        # Les positions normales font un aller-retour
        # exact.
        for position in (10.0, 99.9, 150.0, 400.0):
            traitee = (
                position_originale_vers_traitee(
                    journal,
                    position
                )
            )
            assert (
                position_traitee_vers_originale(
                    journal,
                    traitee
                )
                == pytest.approx(position)
            )

    def test_acceleration_seule(self):
        journal = JournalOperations()
        ajouter_acceleration(journal, 1.5)

        assert (
            position_originale_vers_traitee(
                journal,
                300.0
            )
            == pytest.approx(200.0)
        )
        assert (
            position_traitee_vers_originale(
                journal,
                200.0
            )
            == pytest.approx(300.0)
        )

    def test_composition_complete(self):
        journal = journal_complet()

        attendus = {
            # Avant le premier silence.
            60.0: 24.0,
            # Intérieur du premier silence supprimé :
            # projeté sur la fin de l'audio conservé.
            102.0: 56.2,
            # Entre les deux silences (cumul 4.5 s).
            200.0: 132.4,
            # Après le second silence (cumul 6.5 s).
            600.0: 450.8,
        }

        for originale, traitee in attendus.items():
            assert (
                position_originale_vers_traitee(
                    journal,
                    originale
                )
                == pytest.approx(traitee)
            )

        # Aller-retour exact pour toute position
        # hors des parties supprimées.
        for originale in (60.0, 200.0, 600.0):
            traitee = (
                position_originale_vers_traitee(
                    journal,
                    originale
                )
            )

            assert (
                position_traitee_vers_originale(
                    journal,
                    traitee
                )
                == pytest.approx(originale)
            )

        # Une position dans la partie supprimée se
        # projette sur le début de la coupe, puis
        # revient sur ce début (sémantique des
        # frontières, documentée dans le module).
        assert (
            position_traitee_vers_originale(
                journal,
                56.2
            )
            == pytest.approx(100.25)
        )

    def test_avant_decoupe_composition(self):
        journal = journal_complet()

        assert (
            position_originale_vers_traitee(
                journal,
                10.0
            )
            == 0.0
        )

        # Après la fin conservée : clampée.
        traitee = position_originale_vers_traitee(
            journal,
            1000.0
        )

        assert traitee == pytest.approx(
            (900.0 - 30.0 - 6.5) / 1.25
        )

    def test_aller_retour_systematique(self):
        journal = journal_complet()

        for position in (
            45.0, 90.0, 105.0, 250.0, 480.0,
            550.0, 800.0
        ):
            traitee = (
                position_originale_vers_traitee(
                    journal,
                    position
                )
            )

            assert traitee >= 0.0

            assert (
                position_traitee_vers_originale(
                    journal,
                    traitee
                )
                == pytest.approx(position)
            )


class TestPauseOriginale:
    """
    Durée originale de la pause à une position de
    l'audio traité (signal de coupe P14.4).
    """

    def test_pause_trouvee(self):
        journal = journal_complet()

        # Frontière du premier silence : 100.25 - 30
        # = 70.25 en découpé, / 1.25 = 56.2 traité.
        assert (
            duree_originale_pause(
                journal,
                56.2,
                seuil=1.0
            )
            == pytest.approx(5.0)
        )

        # Dans la marge du buffer conservé (0.25 s
        # avant la coupe, réduit par l'accélération :
        # 0.2 s en traité).
        assert (
            duree_originale_pause(
                journal,
                56.2 - 0.15,
                seuil=1.0
            )
            == pytest.approx(5.0)
        )

        assert (
            duree_originale_pause(
                journal,
                56.2 + 0.15,
                seuil=1.0
            )
            == pytest.approx(5.0)
        )

    def test_pas_de_pause(self):
        journal = journal_complet()

        assert (
            duree_originale_pause(
                journal,
                24.0
            )
            is None
        )

    def test_pause_sous_le_seuil(self):
        journal = JournalOperations()
        ajouter_silence_supprime(
            journal,
            position=100.0,
            duree_originale=0.8,
            buffer=0.1
        )

        assert (
            duree_originale_pause(
                journal,
                100.1,
                seuil=1.0
            )
            is None
        )


def _generer_wav(
    chemin: Path,
    segments
):
    """
    Écrit un WAV mono 16 bits 16 kHz à partir de
    segments (durée_s, amplitude).
    """

    import math

    framerate = 16000

    with wave.open(str(chemin), "w") as fichier:

        fichier.setnchannels(1)
        fichier.setsampwidth(2)
        fichier.setframerate(framerate)

        for duree, amplitude in segments:

            echantillons = int(duree * framerate)

            for i in range(echantillons):

                valeur = int(
                    amplitude
                    * 32767.0
                    * math.sin(
                        2 * math.pi * 440 * i / framerate
                    )
                )

                fichier.writeframes(
                    valeur.to_bytes(2, "little", signed=True)
                )


@pytest.mark.slow
class TestPipelineIntegration:
    """
    Le pipeline journalise l'enchaînement réel :
    découpe, silences (positions et durées
    originales, buffer), accélération.
    """

    def _verifier_ffmpeg(self):
        from services.ffmpeg_paths import (
            get_ffmpeg_path
        )

        ffmpeg = Path(get_ffmpeg_path())

        if not ffmpeg.is_file():
            pytest.skip(
                "FFmpeg indisponible : "
                "test d'intégration ignoré"
            )

    def test_journal_du_pipeline(self, tmp_path):
        self._verifier_ffmpeg()

        source = tmp_path / "source.wav"
        _generer_wav(source, [(3.0, 0.5), (2.0, 0.0), (3.0, 0.5)])

        reglages = AudioProcessingSettings(
            silence_enabled=True,
            silence_threshold_db=-40.0,
            silence_min_duration=1.0,
            silence_buffer_duration=0.2,
        )

        pipeline = AudioProcessingPipeline(
            source,
            source,
            reglages,
            tmp_path / "traite.wav",
            duree_originale=8.0
        )

        sortie = pipeline.run()

        assert sortie.exists()
        assert pipeline.journal is not None

        operations = pipeline.journal.operations

        assert len(operations) == 1
        assert operations[0]["type"] == (
            "silence_supprime"
        )

        # Silence détecté vers 3 s, durée ~2 s
        # (timecodes du contrat, référentiel original).
        position = lire_timecode(
            operations[0]["position"]
        )
        duree = lire_timecode(
            operations[0]["duree_originale"]
        )

        assert 2.0 <= position <= 4.0
        assert 1.5 <= duree <= 2.5
        assert operations[0]["buffer"] == 0.2

        # Pas de découpe ni d'accélération :
        # le fichier journalisé est réinscriptible.
        relu = JournalOperations.from_dict(
            pipeline.journal.to_dict()
        )

        assert relu.operations == operations

    def test_journal_acceleration(self, tmp_path):
        self._verifier_ffmpeg()

        source = tmp_path / "source.wav"
        _generer_wav(source, [(4.0, 0.5)])

        reglages = AudioProcessingSettings(
            speed_enabled=True,
            speed_percent=25,
        )

        pipeline = AudioProcessingPipeline(
            source,
            source,
            reglages,
            tmp_path / "traite.wav",
            duree_originale=4.0
        )

        pipeline.run()

        operations = pipeline.journal.operations

        assert len(operations) == 1
        assert operations[0]["type"] == "acceleration"
        assert operations[0]["facteur"] == (
            pytest.approx(1.25)
        )
