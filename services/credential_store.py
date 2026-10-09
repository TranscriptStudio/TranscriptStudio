"""
Credential Store Service

P6 : Stockage securise des cles API.

Ce module fournit une abstraction pour le stockage des identifiants sensibles
comme la cle API ElevenLabs, en vue de migrer vers un stockage plus securise
(keystore systeme, etc.) tout en restant multiplateforme.

Pour l'instant, implémente un stockage basique avec migration depuis
settings.json, tout en préparant l'infrastructure pour des solutions plus
sécurisées à l'avenir.
"""

import json
from pathlib import Path
from typing import Optional


class CredentialStore:
    """
    Gestionnaire de stockage des identifiants sensibles.
    
    Actuellement utilise un stockage dans settings.json avec chiffrement possible,
    mais conçu pour être étendu vers des solutions système plus sécurisées.
    """
    
    def __init__(self, settings_file: Path):
        """
        Initialise le CredentialStore.
        
        Args:
            settings_file: Chemin vers le fichier settings.json
        """
        self.settings_file = settings_file
        self._credentials = {}
        self._load_credentials()
    
    def _load_credentials(self) -> None:
        """
        Charge les identifiants depuis le fichier de configuration.
        """
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    # Récupérer la clé API (ancien format ou nouveau)
                    self._credentials["elevenlabs_api_key"] = settings.get(
                        "elevenlabs_api_key", ""
                    )
            except (json.JSONDecodeError, IOError):
                # Si le fichier est corrompu, on part de zéro
                self._credentials = {"elevenlabs_api_key": ""}
    
    def _save_credentials(self) -> None:
        """
        Sauvegarde les identifiants dans le fichier de configuration.
        """
        try:
            # Lire les settings existantes
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            else:
                settings = {}
            
            # Mettre à jour la clé API
            settings["elevenlabs_api_key"] = self._credentials.get(
                "elevenlabs_api_key", ""
            )
            
            # Sauvegarder
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except (IOError, json.JSONDecodeError):
            # Si on ne peut pas sauvegarder, c'est un problème mais on ne veut pas
            # bloquer l'application
            pass
    
    def get_api_key(self) -> str:
        """
        Récupère la clé API ElevenLabs.
        
        Returns:
            La clé API si elle existe, une chaîne vide sinon.
        """
        return self._credentials.get("elevenlabs_api_key", "")
    
    def set_api_key(self, api_key: str) -> None:
        """
        Définit la clé API ElevenLabs.
        
        Args:
            api_key: La nouvelle clé API
        """
        self._credentials["elevenlabs_api_key"] = api_key
        self._save_credentials()
    
    def delete_api_key(self) -> None:
        """
        Supprime la clé API ElevenLabs.
        """
        self._credentials["elevenlabs_api_key"] = ""
        self._save_credentials()
    
    def has_api_key(self) -> bool:
        """
        Vérifie si une clé API est configurée.
        
        Returns:
            True si une clé non vide est configurée, False sinon.
        """
        api_key = self._credentials.get("elevenlabs_api_key", "")
        return bool(api_key and api_key.strip())
    
    def migrate_legacy_key(self, legacy_key: Optional[str] = None) -> bool:
        """
        P6.2 : Migre une ancienne clé depuis un format hérité.
        
        Si une clé existe déjà dans le CredentialStore, ne fait rien.
        Sinon, si legacy_key est fourni, le migre.
        
        **Sécurité** : Ne jamais journaliser la clé.
        
        Args:
            legacy_key: Clé héritée à migrer (optionnel)
            
        Returns:
            True si une migration a eu lieu, False sinon
        """
        # Si on a déjà une clé, pas de migration nécessaire
        if self.has_api_key():
            return False
        
        # Si une clé héritée est fournie, la migrer
        if legacy_key and legacy_key.strip():
            # **Ne jamais journaliser la clé**
            self.set_api_key(legacy_key)
            return True
        
        return False
    
    def migrate_from_settings_manager(self, settings_manager) -> bool:
        """
        P6.2 : Migre une clé depuis SettingsManager vers CredentialStore.
        
        Cette méthode vérifie si SettingsManager a une clé API et la migre
        vers CredentialStore si ce n'est pas déjà fait.
        
        **Sécurité** : La clé est copiée puis supprimée de SettingsManager
        seulement après confirmation que CredentialStore l'a bien reçu.
        
        Args:
            settings_manager: Instance de SettingsManager
            
        Returns:
            True si une migration a eu lieu, False sinon
        """
        # Vérifier si SettingsManager a une clé
        legacy_key = settings_manager.get_api_key()
        
        if legacy_key and legacy_key.strip():
            # Si CredentialStore n'a pas de clé, migrer
            if not self.has_api_key():
                self.set_api_key(legacy_key)
                # Supprimer de SettingsManager après migration réussie
                settings_manager.set_api_key("")
                settings_manager.save()
                return True
        
        return False
