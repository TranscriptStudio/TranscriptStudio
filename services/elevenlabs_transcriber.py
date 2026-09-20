import json

from pathlib import Path

import requests

from services.settings import (
    SettingsManager
)

class ElevenLabsTranscriber:

    def __init__(self):

        settings = SettingsManager()

        self.api_key = settings.get_api_key()

    def test_connection(self):

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

            return (
                False,
                f"Erreur HTTP {response.status_code}"
            )

        except Exception as e:

            return (
                False,
                str(e)
            )

    def transcribe(
        self,
        audio_file,
        options
    ):

        with open(audio_file, "rb") as f:

            files = {
                "file": f
            }

            data = {

                "model_id":
                    options["model_id"],

                "tag_audio_events":
                    str(False).lower(),

                "language_code":
                    options["language_code"],

                "diarize":
                    str(
                        options["diarize"]
                    ).lower(),

                "no_verbatim":
                    str(
                        options["no_verbatim"]
                    ).lower(),

                "use_speaker_library":
                    str(
                        options["use_speaker_library"]
                    ).lower(),

                "detect_speaker_roles":
                    str(
                        options[
                            "detect_speaker_roles"
                        ]
                    ).lower()
            }

            if options["keyterms"]:

                data["keyterms"] = (
                    options["keyterms"]
                )

            response = requests.post(

                "https://api.elevenlabs.io/v1/speech-to-text",

                headers={
                    "xi-api-key":
                        self.api_key
                },

                files=files,

                data=data,

                timeout=3600
            )

        response.raise_for_status()

        return response.json()


