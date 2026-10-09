"""
Tests unitaires pour services/api_capabilities.py

P7 : Tests automatisés pour le mode sans API
"""

import pytest

from services.api_capabilities import (
    has_api_key,
    has_transcription_api,
    can_transcribe_direct,
    can_finalize_audio,
    can_access_account_info,
    APICapabilityManager,
)


class TestAPICapabilities:
    """Tests pour les fonctions de capabilities API"""
    
    def test_can_finalize_audio_always_true(self):
        """Test que can_finalize_audio retourne toujours True."""
        assert can_finalize_audio() is True
    
    def test_api_capability_manager_instances(self):
        """Test la création d'instances APICapabilityManager."""
        manager = APICapabilityManager()
        assert manager is not None
        
        # Vérifier que les méthodes existent
        assert hasattr(manager, 'has_api_key')
        assert hasattr(manager, 'has_transcription_api')
        assert hasattr(manager, 'can_transcribe_direct')
        assert hasattr(manager, 'can_finalize_audio')
        assert hasattr(manager, 'can_access_account_info')
        assert hasattr(manager, 'require_api_key')


class TestAPICapabilityManager:
    """Tests pour la classe APICapabilityManager"""
    
    def test_can_finalize_audio_always_true(self):
        """Test que can_finalize_audio retourne toujours True."""
        manager = APICapabilityManager()
        assert manager.can_finalize_audio() is True
    
    def test_consistency_between_functions_and_manager(self):
        """Test la cohérence entre fonctions et manager."""
        manager = APICapabilityManager()
        
        # Les résultats doivent être cohérents
        assert has_api_key() == manager.has_api_key()
        assert has_transcription_api() == manager.has_transcription_api()
        assert can_transcribe_direct() == manager.can_transcribe_direct()
        assert can_finalize_audio() == manager.can_finalize_audio()
        assert can_access_account_info() == manager.can_access_account_info()
