from datetime import datetime

import requests

from services.credential_store import CredentialStore
from services.settings import APP_DATA_DIR
from services.api_capabilities import has_api_key


class ElevenLabsAPI:

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self):

        # P6 : Utiliser CredentialStore pour la clé API
        credential_store = CredentialStore(APP_DATA_DIR / "settings.json")
        
        self.api_key = (
            credential_store.get_api_key()
        )

        self.headers = {
            "xi-api-key": self.api_key
        }
        
        # Vérifier que la clé API est disponible
        if not has_api_key():
            raise ValueError("Clé API ElevenLabs manquante. Impossible d'initialiser l'API ElevenLabs.")

    def get_account_info(self):

        response = requests.get(
            f"{self.BASE_URL}/user",
            headers=self.headers,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    def get_account_summary(self):

        data = self.get_account_info()

        subscription = data["subscription"]

        remaining = (
            subscription["character_limit"]
            - subscription["character_count"]
        )
        used = subscription[
            "character_count"
        ]

        limit = subscription[
            "character_limit"
        ]

        usage_percent = (
            used / limit * 100
            if limit > 0
            else 0
        )

        return {

            "name":
                data.get(
                    "first_name",
                    ""
                ),

            "tier":
                subscription["tier"],

            "status":
                subscription["status"],

            "remaining":
                remaining,

            "used":
                subscription["character_count"],
            "limit":
                subscription["character_limit"],

            "utilization" : usage_percent,

            "voice_limit":
                subscription["voice_limit"],

            "instant_clone":
                subscription[
                    "can_use_instant_voice_cloning"
                ],

            "professional_clone":
                subscription[
                    "can_use_professional_voice_cloning"
                ],

            "reset_date":
                datetime.fromtimestamp(
                    subscription[
                        "next_character_count_reset_unix"
                    ]
                )
        }