from pathlib import Path
from datetime import datetime
import shutil
import json
import re
from services.settings import (
    SettingsManager
)



class ProjectManager:

    def __init__(self):

        settings = SettingsManager()

        self.root = Path(
            settings.get_projects_root()
        )

        self.root.mkdir(
            parents=True,
            exist_ok=True
        )


    def create_project_folder(
        self,
        audio_file,
        category=""
    ):

        date_prefix = datetime.now().strftime(
            "%Y-%m-%d"
        )

        audio_name = Path(
            audio_file
        ).stem

        audio_name = re.sub(
            r'[\\/:*?"<>|]',
            "_",
            audio_name
        )

        folder_name = (
            f"{date_prefix}_{audio_name}"
        )

        base_folder = self.root

        if category:

            base_folder = (
                self.root
                / category
            )

        base_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        folder = (
            base_folder
            / folder_name
        )

        counter = 1
        while folder.exists():
            folder = (
                base_folder
                / f"{folder_name}_{counter}"
            )
            counter += 1
        

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        return folder

    def copy_audio_file(
        self,
        source_audio,
        project_folder
    ):

        source = Path(source_audio)

        destination = (
            project_folder
            / source.name
        )

        shutil.copy2(
            source,
            destination
        )

        return destination

    def save_transcription_json(
        self,
        data,
        project_folder
    ):

        json_file = (
            project_folder
            / "transcription.json"
        )

        with open(
            json_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        return json_file






    