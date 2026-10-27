"""
Tests unitaires pour services/ffmpeg_paths.py

P7 : Tests automatisés pour la résolution FFmpeg multiplateforme
"""

import sys
from unittest.mock import patch

import pytest

from services.ffmpeg_paths import (
    FFMPEG_DIR,
    FFMPEG_NAME,
    FFMPEG_PATH,
    get_ffmpeg_path,
)


class TestFFmpegPaths:
    """Tests pour les variables de chemins FFmpeg"""
    
    def test_ffmpeg_name_windows(self):
        """Test que FFMPEG_NAME est ffmpeg.exe sur Windows."""
        import importlib
        import services.ffmpeg_paths
        try:
            with patch('sys.platform', 'win32'):
                # Recharger le module pour prendre en compte le mock
                importlib.reload(services.ffmpeg_paths)
                
                assert services.ffmpeg_paths.FFMPEG_NAME == "ffmpeg.exe"
        finally:
            # Restaurer le module avec la vraie plateforme :
            # le reload sous mock contamine sinon toute la suite.
            importlib.reload(services.ffmpeg_paths)
    
    def test_ffmpeg_name_non_windows(self):
        """Test que FFMPEG_NAME est ffmpeg sur les autres plateformes."""
        import importlib
        import services.ffmpeg_paths
        try:
            with patch('sys.platform', 'linux'):
                importlib.reload(services.ffmpeg_paths)
                
                assert services.ffmpeg_paths.FFMPEG_NAME == "ffmpeg"
        finally:
            importlib.reload(services.ffmpeg_paths)
    
    def test_ffmpeg_dir_is_path(self):
        """Test que FFMPEG_DIR est un objet Path."""
        from pathlib import Path
        assert isinstance(FFMPEG_DIR, Path)
    
    def test_ffmpeg_path_is_path(self):
        """Test que FFMPEG_PATH est un objet Path."""
        from pathlib import Path
        assert isinstance(FFMPEG_PATH, Path)


class TestFindFFmpegPath:
    """Tests pour la fonction find_ffmpeg_path"""
    
    def test_get_ffmpeg_path_returns_path(self):
        """Test que get_ffmpeg_path retourne un Path."""
        from pathlib import Path
        result = get_ffmpeg_path()
        assert isinstance(result, Path)
