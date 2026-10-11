import json

from pathlib import Path

import requests

from services.credential_store import CredentialStore
from services.settings import APP_DATA_DIR

class ElevenLabsTranscriber:

    def __init__(self):

        # P6 : Utiliser CredentialStore pour la clé API
        credential_store = CredentialStore(APP_DATA_DIR / "settings.json")
        self.api_key = credential_store.get_api_key()

    def test_connection(self):

        # Verifier si la cle est vide
        if not self.api_key or not self.api_key.strip():
            return (
                False,
                "Clé API manquante. Veuillez renseigner une clé API ElevenLabs valide."
            )
        
        try:

            response = requests.get(
                "https://api.elevenlabs.io/v1/user",
                headers={
                    "xi-api-key": self.api_key
                },
                timeout=10
            )

            print("STATUS =", response.status_code)
            print("BODY =", response.text)

            if response.status_code == 200:

                return (
                    True,
                    "Connexion ElevenLabs réussie"
                )
            
            # Gestion des erreurs HTTP specifiques
            if response.status_code == 401:
                return (
                    False,
                    "Clé API invalide. Veuillez vérifier que votre clé ElevenLabs est correcte."
                )
            
            if response.status_code == 403:
                return (
                    False,
                    "Accès refusé. Votre clé API peut être désactivée ou avoir atteint ses limites."
                )

            return (
                False,
                f"Erreur HTTP {response.status_code}: {response.text[:100]}"  # Limiter la longueur
            )

        except requests.exceptions.Timeout:
            return (
                False,
                "La connexion a expiré. Vérifiez votre connexion Internet."
            )
        
        except requests.exceptions.ConnectionError:
            return (
                False,
                "Impossible de se connecter au serveur ElevenLabs. Vérifiez votre connexion Internet."
            )
        
        except Exception as e:
            # Pour toute autre exception, retourner un message generique
            # Sans les details techniques qui pourraient fuiter des infos sensibles
            return (
                False,
                f"Une erreur est survenue: {type(e).__name__}"
            )

    def transcribe(
        self,
        audio_file,
        options
    ):
        
        # Verifier la presence de la cle API
        if not self.api_key or not self.api_key.strip():
            raise ValueError("Clé API manquante. Veuillez renseigner une clé API ElevenLabs valide pour lancer la transcription.")
        
        try:
            data = {
                "model_id": options["model_id"],
                "tag_audio_events": str(False).lower(),
                "language_code": options["language_code"],
                "diarize": str(options["diarize"]).lower(),
                "no_verbatim": str(options["no_verbatim"]).lower(),
                "use_speaker_library": str(options["use_speaker_library"]).lower(),
                "detect_speaker_roles": str(options["detect_speaker_roles"]).lower()
            }
            
            if options["keyterms"]:
                data["keyterms"] = options["keyterms"]
            
            # Le fichier doit rester ouvert pendant l'envoi :
            # requests lit son contenu a la construction de la
            # requete multipart. Fermer le fichier avant
            # requests.post leve "ValueError: read of closed file".
            with open(audio_file, "rb") as f:
                files = {"file": f}
            
                response = requests.post(
                    "https://api.elevenlabs.io/v1/speech-to-text",
                    headers={"xi-api-key": self.api_key},
                    files=files,
                    data=data,
                    timeout=3600
                )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            # Gérer les erreurs de manière graceuse avec des messages clairs
            error_msg = "Clé API manquante ou invalide. Veuillez renseigner une clé API ElevenLabs valide pour lancer la transcription."
            if isinstance(e, ValueError) and "Clé API" in str(e):
                error_msg = str(e)
            elif isinstance(e, requests.exceptions.HTTPError):
                result = self._handle_api_error(e)
                error_msg = result[1]
            elif isinstance(e, requests.exceptions.Timeout):
                error_msg = "La transcription a expiré. Vérifiez votre connexion Internet."
            elif isinstance(e, requests.exceptions.ConnectionError):
                error_msg = "Impossible de se connecter au serveur ElevenLabs. Vérifiez votre connexion Internet."
            else:
                error_msg = f"Erreur lors de la transcription: {type(e).__name__}: {e}"
            
            raise RuntimeError(error_msg)
    
    def _handle_api_error(self, exception: Exception) -> tuple[False, str]:
        """
        Gère les erreurs API et retourne un message utilisateur clair.
        """
        import requests
        
        if isinstance(exception, requests.exceptions.HTTPError):
            response = exception.response
            if response.status_code == 401:
                return (
                    False,
                    "Clé API manquante ou invalide. Veuillez renseigner une clé API ElevenLabs valide pour lancer la transcription."
                )
            if response.status_code == 403:
                return (
                    False,
                    "Accès refusé. Votre clé API peut être désactivée ou avoir atteint ses limites."
                )
            return (
                False,
                f"Erreur API ({response.status_code}): {response.text[:100]}"
            )
        
        if isinstance(exception, requests.exceptions.Timeout):
            return (
                False,
                "La transcription a expiré. Vérifiez votre connexion Internet."
            )
        
        if isinstance(exception, requests.exceptions.ConnectionError):
            return (
                False,
                "Impossible de se connecter au serveur ElevenLabs. Vérifiez votre connexion Internet."
            )
        
        return (
            False,
            f"Erreur lors de la transcription: {type(exception).__name__}"
        )


