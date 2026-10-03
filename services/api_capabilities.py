"""
API Capabilities Manager

Centralise la gestion des capacités API pour éviter les tests dispersés
et permettre un découplage propre entre les fonctionnalités et la disponibilité
de l'API ElevenLabs.

Ce module expose des fonctions simples pour vérifier si certaines opérations
sont disponibles, sans avoir à vérifier manuellement la présence de la clé API.
"""

from services.settings import SettingsManager


def has_api_key() -> bool:
    """
    Vérifie si une clé API ElevenLabs est configurée.
    
    Returns:
        bool: True si une clé API non vide est configurée, False sinon.
    """
    settings = SettingsManager()
    api_key = settings.get_api_key()
    return bool(api_key and api_key.strip())


def has_transcription_api() -> bool:
    """
    Vérifie si la capacité de transcription est disponible.
    
    La transcription nécessite une clé API ElevenLabs valide.
    
    Returns:
        bool: True si la transcription est possible, False sinon.
    """
    return has_api_key()


def can_transcribe_direct() -> bool:
    """
    Vérifie si la transcription directe est disponible.
    
    La transcription directe nécessite une clé API ElevenLabs valide.
    
    Returns:
        bool: True si la transcription directe est possible, False sinon.
    """
    return has_transcription_api()


def can_finalize_audio() -> bool:
    """
    Vérifie si la finalisation audio est disponible.
    
    La finalisation audio (pretraitement, export) ne nécessite PAS de clé API
    car elle utilise uniquement FFmpeg localement.
    
    Returns:
        bool: Toujours True, car la finalisation audio est indépendante de l'API.
    """
    return True


def can_access_account_info() -> bool:
    """
    Vérifie si l'accès aux informations de compte est disponible.
    
    L'accès aux informations de compte nécessite une clé API ElevenLabs valide.
    
    Returns:
        bool: True si l'accès au compte est possible, False sinon.
    """
    return has_api_key()


def require_api_key(message: str = None) -> None:
    """
    Lève une exception si aucune clé API n'est disponible.
    
    Args:
        message: Message personnalisé à inclure dans l'exception.
        
    Raises:
        ValueError: Si aucune clé API n'est configurée.
    """
    if not has_api_key():
        error_msg = message or "Clé API manquante. Veuillez renseigner une clé API ElevenLabs valide."
        raise ValueError(error_msg)


class APICapabilityManager:
    """
    Gestionnaire des capacités API (pour une utilisation plus orientée objet).
    
    Cette classe permet de vérifier les capacités de manière centralisée
    et peut être étendue pour supporter plusieurs fournisseurs d'API.
    """
    
    def __init__(self):
        self._settings = SettingsManager()
    
    def has_api_key(self) -> bool:
        """Vérifie si une clé API est configurée."""
        api_key = self._settings.get_api_key()
        return bool(api_key and api_key.strip())
    
    def has_transcription_api(self) -> bool:
        """Vérifie si la transcription est disponible."""
        return self.has_api_key()
    
    def can_transcribe_direct(self) -> bool:
        """Vérifie si la transcription directe est disponible."""
        return self.has_transcription_api()
    
    def can_finalize_audio(self) -> bool:
        """Vérifie si la finalisation audio est disponible."""
        return True
    
    def can_access_account_info(self) -> bool:
        """Vérifie si l'accès aux informations de compte est disponible."""
        return self.has_api_key()
    
    def require_api_key(self, message: str = None) -> None:
        """Lève une exception si aucune clé API n'est disponible."""
        if not self.has_api_key():
            error_msg = message or "Clé API manquante. Veuillez renseigner une clé API ElevenLabs valide."
            raise ValueError(error_msg)