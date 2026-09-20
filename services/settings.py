import json
from pathlib import Path
from services.app_paths import (
    APP_DATA_DIR,
    PROJECTS_DIR,
)

class SettingsManager:

    def __init__(self):

        self.app_folder = APP_DATA_DIR

        self.app_folder.mkdir(
            exist_ok=True
        )

        self.settings_file = (
            self.app_folder
            / "settings.json"
        )

        self.settings = {}

        self.load()

    def load(self):

        if not self.settings_file.exists():

            self.settings = (
                self.default_settings()
            )

            self.save()

            return

        with open(
            self.settings_file,
            "r",
            encoding="utf-8"
        ) as f:

            self.settings = json.load(f)
            defaults = self.default_settings()

            for key, value in defaults.items():

                if key not in self.settings:

                    self.settings[key] = value

            self.save()

    def save(self):

        with open(
            self.settings_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.settings,
                f,
                ensure_ascii=False,
                indent=2
            )

    def default_settings(self):

        return {

            "elevenlabs_api_key": "",

            "recent_projects": [],

            "transcription_defaults": {

                "model_id": "scribe_v2","language_code": "fr",

                "diarize": True,

                "no_verbatim": True,

                "use_speaker_library": True,

                "detect_speaker_roles": False

            },
            "projects_root": str(
                PROJECTS_DIR
            ),
        }

    def get_api_key(self):

        return self.settings.get(
            "elevenlabs_api_key",
            ""
        )

    def set_api_key(
        self,
        api_key
    ):

        self.settings[
            "elevenlabs_api_key"
        ] = api_key

        self.save()

    def get_recent_projects(self):

        return self.settings.get(
            "recent_projects",
            []
        )

    def add_recent_project(
        self,
        project_path
    ):

        projects = (
            self.settings.setdefault(
                "recent_projects",
                []
            )
        )

        project_path = str(
            Path(project_path)
        )

        if project_path in projects:

            projects.remove(
                project_path
            )

        projects.insert(
            0,
            project_path
        )

        self.settings[
            "recent_projects"
        ] = projects[:20]

        self.save()

    def get_transcription_defaults(self):

        return self.settings.get(
            "transcription_defaults",
            {}
        )

    def update_transcription_defaults(
        self,
        **kwargs
    ):

        defaults = self.settings.setdefault(
            "transcription_defaults",
            {}
        )

        defaults.update(kwargs)

        self.save()

    def get_projects_root(self):

        return self.settings.get(
            "projects_root",
            str(PROJECTS_DIR)
        )

    def set_projects_root(
        self,
        folder
    ):

        self.settings[
            "projects_root"
        ] = str(folder)

        self.save()










