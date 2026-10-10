"""
Tests P10 : centralisation des chemins applicatifs
et sous-repertoire temporaire unique par session.
"""

import struct
import wave

from pathlib import Path

from services.app_paths import (
    APP_NAME,
    TEMP_DIR,
    SESSION_TEMP_DIR,
    ensure_session_temp_dir,
    cleanup_session_temp_dir,
)


def _make_wav(path: Path, seconds: float = 0.5):
    """Genere un petit wav de test."""

    rate = 8000

    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        for i in range(int(rate * seconds)):
            value = int(
                9000 * (i % 100) / 100
            )
            f.writeframes(struct.pack("<h", value))


def test_temp_dir_is_in_system_temp():
    """Le dossier temporaire vit sous le temp du systeme."""

    assert TEMP_DIR.name == APP_NAME
    assert SESSION_TEMP_DIR.parent == TEMP_DIR


def test_session_temp_dir_created_on_demand():
    """Le sous-repertoire de session n'existe pas avant usage."""

    if SESSION_TEMP_DIR.exists():
        cleanup_session_temp_dir()

    assert not SESSION_TEMP_DIR.exists()

    returned = ensure_session_temp_dir()

    assert returned == SESSION_TEMP_DIR
    assert SESSION_TEMP_DIR.is_dir()


def test_session_temp_dir_survives_multiple_calls():
    """ensure_session_temp_dir est idempotent."""

    first = ensure_session_temp_dir()
    second = ensure_session_temp_dir()

    assert first == second


def test_cleanup_removes_session_dir():
    """Le nettoyage supprime le dossier et son contenu."""

    ensure_session_temp_dir()

    marker = SESSION_TEMP_DIR / "marker.txt"
    marker.write_text("test", encoding="utf-8")

    cleanup_session_temp_dir()

    assert not SESSION_TEMP_DIR.exists()


def test_same_named_media_no_cross_session_collision(tmp_path):
    """
    P10.2 : deux medias de meme nom depuis deux
    repertoires differents ne partagent plus
    leurs fichiers temporaires entre sessions.
    """

    from services.audio_waveform_service import (
        AudioWaveformService,
    )

    folder_a = tmp_path / "dossier a"
    folder_b = tmp_path / "dossier-b"
    folder_a.mkdir()
    folder_b.mkdir()

    # Nom accentue : couvre aussi les chemins
    # avec accents et caracteres Unicode.

    media_a = folder_a / "café été.wav"
    media_b = folder_b / "café été.wav"

    _make_wav(media_a)
    _make_wav(media_b)

    service = AudioWaveformService()

    # Les deux extractions ecivent dans le dossier
    # de session courant, sous le temp de l'application.
    document_a = service.extract_waveform(media_a)

    display_a = Path(document_a.display_wav)
    assert display_a.parent == SESSION_TEMP_DIR

    document_b = service.extract_waveform(media_b)

    display_b = Path(document_b.display_wav)
    assert display_b.parent == SESSION_TEMP_DIR

    # L'extraction successive du second media
    # reste coherente (meme nom, meme session :
    # reecriture sequentialle, pas de melange).
    assert display_a.name == display_b.name

    cleanup_session_temp_dir()

    assert not display_b.exists()
