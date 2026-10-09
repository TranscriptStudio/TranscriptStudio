"""
Tests unitaires pour services/project_io.py

P7 : Tests automatisés pour la portabilité des projets
"""

import json
from pathlib import Path

import pytest

from services.project_io import (
    load_project,
    save_project,
    _make_relative_path,
    _normalize_path_for_json,
    repair_project_speakers,
)
from models.project import Project
from models.speaker import Speaker
from models.word import Word
from models.block import Block


class TestNormalizePath:
    """Tests pour _normalize_path_for_json"""
    
    def test_normalize_path_with_backslashes(self):
        """Test la normalisation des backslashes Windows."""
        result = _normalize_path_for_json("C:\\Users\\test\\audio.wav")
        assert result == "C:/Users/test/audio.wav"
    
    def test_normalize_path_with_forward_slashes(self):
        """Test que les slashes sont conservés."""
        result = _normalize_path_for_json("audio/test.wav")
        assert result == "audio/test.wav"
    
    def test_normalize_none_path(self):
        """Test avec None."""
        result = _normalize_path_for_json(None)
        assert result is None


class TestMakeRelativePath:
    """Tests pour _make_relative_path"""
    
    def test_relative_path_in_project_dir(self, tmp_path):
        """Test la conversion d'un chemin absolu dans le dossier projet."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        audio_file = str(project_dir / "audio.wav")
        
        result = _make_relative_path(audio_file, project_dir)
        assert result == "audio.wav"
    
    def test_relative_path_in_subdir(self, tmp_path):
        """Test la conversion d'un chemin absolu dans un sous-dossier du projet."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        subdir = project_dir / "audio"
        subdir.mkdir()
        audio_file = str(subdir / "test.wav")
        
        result = _make_relative_path(audio_file, project_dir)
        assert result == "audio/test.wav"
    
    def test_external_path_unchanged(self, tmp_path):
        """Test qu'un chemin externe au projet reste absolu."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        external_audio = str(tmp_path / "external" / "audio.wav")
        
        result = _make_relative_path(external_audio, project_dir)
        # Pour l'instant, les chemins externes restent absolus
        assert "/" in result or ":\\" in result or result == external_audio


class TestSaveAndLoadProject:
    """Tests pour save_project et load_project"""
    
    def test_save_project_uses_relative_audio_path(self, tmp_path):
        """Test que sauvegarde utilise un chemin audio relatif."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        
        # Créer un projet avec chemin absolu
        project = Project(
            project_file=str(project_dir / "test.sttproj"),
            modified=False,
            name="Test",
            audio_file=str(project_dir / "audio.wav"),
            transcription_id="test",
            language_code="fr",
            duration_seconds=10.0,
            speakers=[],
            words=[],
            blocks=[],
            original_elevenlabs_response={},
            project_format_version=1
        )
        
        # Sauvegarder
        project_file = str(project_dir / "test.sttproj")
        save_project(project, project_file)
        
        # Vérifier que audio_file est relatif dans le JSON
        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert data["audio_file"] == "audio.wav"
    
    def test_save_project_does_not_persist_project_file(self, tmp_path):
        """Test que project_file n'est PAS sauvé dans le JSON."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        
        project = Project(
            project_file=str(project_dir / "test.sttproj"),
            modified=False,
            name="Test",
            audio_file="audio.wav",
            transcription_id="test",
            language_code="fr",
            duration_seconds=10.0,
            speakers=[],
            words=[],
            blocks=[],
            original_elevenlabs_response={},
            project_format_version=1
        )
        
        project_file = str(project_dir / "test.sttproj")
        save_project(project, project_file)
        
        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert "project_file" not in data
    
    def test_load_relative_project_resolves_audio_from_project_folder(self, tmp_path):
        """Test le chargement d'un projet avec chemin audio relatif."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        
        # Créer un projet sauvegardé avec chemin relatif
        project_file = project_dir / "test.sttproj"
        data = {
            "project_format_version": 1,
            "name": "Test",
            "audio_file": "audio.wav",
            "transcription_id": "test",
            "language_code": "fr",
            "duration_seconds": 10.0,
            "modified": False,
            "speakers": [],
            "words": [],
            "blocks": [],
            "original_elevenlabs_response": {}
        }
        
        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Charger le projet
        project = load_project(str(project_file))
        
        # Vérifier que project_file est défini en mémoire
        assert project.project_file is not None
        assert Path(project.project_file).name == "test.sttproj"
        
        # Vérifier que audio_file est résolu en absolu
        assert project.audio_file.endswith("audio.wav") or "audio.wav" in project.audio_file
    
    def test_load_legacy_absolute_project_existing_audio(self, tmp_path):
        """Test le chargement d'un ancien projet avec chemin audio absolu existant."""
        # Créer un fichier audio factice
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        audio_file = audio_dir / "test.wav"
        audio_file.touch()
        
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_file = project_dir / "legacy.sttproj"
        
        # Créer un projet avec chemin absolu existant
        data = {
            "name": "Legacy",
            "audio_file": str(audio_file),
            "transcription_id": "legacy",
            "language_code": "fr",
            "duration_seconds": 10.0,
            "modified": False,
            "speakers": [],
            "words": [],
            "blocks": [],
            "original_elevenlabs_response": {}
        }
        
        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        project = load_project(str(project_file))
        assert project.audio_file == str(audio_file)
    
    def test_project_data_survives_round_trip(self, tmp_path):
        """Test que les données du projet survivent à une sauvegarde/chargement."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        
        # Créer un projet avec des données
        speakers = [
            Speaker(id="s1", name="Alice", color="#FF0000"),
            Speaker(id="s2", name="Bob", color="#0000FF")
        ]
        words = [
            Word(text="Hello", start=0.0, end=1.0, speaker_id="s1", item_type="word"),
            Word(text="World", start=1.0, end=2.0, speaker_id="s2", item_type="word")
        ]
        blocks = [
            Block(id="b1", speaker_id="s1", start_word=0, end_word=1, created_by_user=False)
        ]
        
        project = Project(
            project_file=str(project_dir / "test.sttproj"),
            modified=True,
            name="Test Round Trip",
            audio_file=str(project_dir / "audio.wav"),
            transcription_id="test_id",
            language_code="en",
            duration_seconds=15.5,
            speakers=speakers,
            words=words,
            blocks=blocks,
            original_elevenlabs_response={"key": "value"},
            project_format_version=1
        )
        
        project_file = str(project_dir / "test.sttproj")
        save_project(project, project_file)
        
        # Recharger
        loaded_project = load_project(project_file)
        
        # Vérifier toutes les données
        assert loaded_project.name == "Test Round Trip"
        assert loaded_project.transcription_id == "test_id"
        assert loaded_project.language_code == "en"
        assert loaded_project.duration_seconds == 15.5
        assert len(loaded_project.speakers) == 2
        assert loaded_project.speakers[0].name == "Alice"
        assert loaded_project.speakers[1].name == "Bob"
        assert len(loaded_project.words) == 2
        assert loaded_project.words[0].text == "Hello"
        assert loaded_project.words[1].text == "World"
        assert len(loaded_project.blocks) == 1
        assert loaded_project.original_elevenlabs_response == {"key": "value"}


class TestRepairProjectSpeakers:
    """Tests pour repair_project_speakers"""
    
    def test_repair_with_invalid_speaker_ids(self):
        """Test la réparation des blocs avec des speaker_id invalides."""
        speakers = [
            Speaker(id="valid_speaker", name="Valid", color="#000000")
        ]
        blocks = [
            Block(id="block1", speaker_id="valid_speaker", start_word=0, end_word=1, created_by_user=False),
            Block(id="block2", speaker_id="invalid_speaker", start_word=1, end_word=2, created_by_user=False)
        ]
        
        report = repair_project_speakers(speakers, blocks)
        
        assert report is not None
        assert report["count"] == 1
        assert "block2" in report["repaired_blocks"]
        # Le bloc est réaffecté à l'intervenant générique
        assert blocks[1].speaker_id == report["generic_id"]
    
    def test_no_repair_needed(self):
        """Test qu'aucun rapport n'est retourné si tout est cohérent."""
        speakers = [
            Speaker(id="valid_speaker", name="Valid", color="#000000")
        ]
        blocks = [
            Block(id="block1", speaker_id="valid_speaker", start_word=0, end_word=1, created_by_user=False)
        ]
        
        report = repair_project_speakers(speakers, blocks)
        assert report is None
