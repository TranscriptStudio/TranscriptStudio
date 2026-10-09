"""
Pytest fixtures pour TranscriptStudio

P7 : Tests automatisés
"""

import json
from pathlib import Path
import pytest

from models.project import Project
from models.speaker import Speaker
from models.word import Word
from models.block import Block


@pytest.fixture
def temp_project_dir(tmp_path):
    """Crée un répertoire temporaire pour les tests de projet."""
    return tmp_path


@pytest.fixture
def sample_speakers():
    """Crée une liste d'intervenants pour les tests."""
    return [
        Speaker(id="speaker_1", name="Alice", color="#FF0000"),
        Speaker(id="speaker_2", name="Bob", color="#0000FF"),
    ]


@pytest.fixture
def sample_words():
    """Crée une liste de mots pour les tests."""
    return [
        Word(text="Bonjour", start=0.0, end=1.0, speaker_id="speaker_1", item_type="word"),
        Word(text="tout", start=1.0, end=1.5, speaker_id="speaker_1", item_type="word"),
        Word(text="le", start=1.5, end=1.8, speaker_id="speaker_1", item_type="word"),
        Word(text="monde", start=1.8, end=2.5, speaker_id="speaker_1", item_type="word"),
    ]


@pytest.fixture
def sample_blocks():
    """Crée une liste de blocs pour les tests."""
    return [
        Block(id="block_1", speaker_id="speaker_1", start_word=0, end_word=3, created_by_user=False),
    ]


@pytest.fixture
def sample_project(temp_project_dir):
    """Crée un projet de test avec des données de base."""
    return Project(
        project_file=str(temp_project_dir / "test.sttproj"),
        modified=False,
        name="Test Project",
        audio_file="test.wav",
        transcription_id="test_transcription",
        language_code="fr",
        duration_seconds=10.0,
        speakers=[],
        words=[],
        blocks=[],
        original_elevenlabs_response={},
        project_format_version=1
    )


@pytest.fixture
def portable_project_file(temp_project_dir, sample_speakers, sample_words, sample_blocks):
    """Crée un fichier de projet portable avec chemin audio relatif."""
    project_file = temp_project_dir / "portable.sttproj"
    
    # Créer un projet
    project = Project(
        project_file=str(project_file),
        modified=False,
        name="Portable Project",
        audio_file="audio/test.wav",  # Chemin relatif
        transcription_id="test_transcription",
        language_code="fr",
        duration_seconds=10.0,
        speakers=sample_speakers,
        words=sample_words,
        blocks=sample_blocks,
        original_elevenlabs_response={},
        project_format_version=1
    )
    
    # Sauvegarder le projet (simule ce que fait save_project)
    data = {
        "project_format_version": project.project_format_version,
        "name": project.name,
        "audio_file": project.audio_file,  # Chemin relatif
        "transcription_id": project.transcription_id,
        "language_code": project.language_code,
        "duration_seconds": project.duration_seconds,
        "modified": project.modified,
        "speakers": [
            {"id": s.id, "name": s.name, "color": s.color}
            for s in project.speakers
        ],
        "words": [
            {"text": w.text, "start": w.start, "end": w.end, "speaker_id": w.speaker_id, "item_type": w.item_type}
            for w in project.words
        ],
        "blocks": [
            {"id": b.id, "speaker_id": b.speaker_id, "start_word": b.start_word, "end_word": b.end_word, "created_by_user": b.created_by_user}
            for b in project.blocks
        ],
        "original_elevenlabs_response": project.original_elevenlabs_response
    }
    
    with open(project_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return project_file


@pytest.fixture
def legacy_project_file(temp_project_dir):
    """Crée un fichier de projet ancien avec chemin audio absolu."""
    project_file = temp_project_dir / "legacy.sttproj"
    
    # Chemin absolu fictif (pour simuler un ancien projet)
    abs_audio_path = "/old/path/to/audio.wav"
    
    data = {
        "name": "Legacy Project",
        "audio_file": abs_audio_path,  # Chemin absolu
        "transcription_id": "legacy_transcription",
        "language_code": "fr",
        "duration_seconds": 15.0,
        "modified": False,
        "project_file": str(project_file),  # Ancien format : project_file dans le JSON
        "speakers": [],
        "words": [],
        "blocks": [],
        "original_elevenlabs_response": {}
    }
    
    with open(project_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return project_file
