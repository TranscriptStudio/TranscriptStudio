from pathlib import Path
from datetime import datetime
import shutil
import json
import re
import time
from services.settings import (
    SettingsManager
)

DEFAULT_CATEGORY = "Commun"

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

        #
        # Répertoire de classement utilisé
        # par défaut pour les nouveaux projets.
        #
        self.default_category = (
            DEFAULT_CATEGORY
        )

        self.ensure_default_category()

    def ensure_default_category(self):
        """
        Garantit l'existence du répertoire
        de classement par défaut.
        """
        default_folder = (
            self.root
            / self.default_category
        )

        default_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        return default_folder


    def get_categories(self):
        """
        Retourne les sous-répertoires existants
        du répertoire racine des projets.
        """

        self.ensure_default_category()

        categories = sorted(
            (
                item.name
                for item in self.root.iterdir()
                if item.is_dir()
            ),
            key=str.casefold
        )

        #
        # Commun reste toujours en première
        # position dans la liste.
        #
        categories = [
            category
            for category in categories
            if category.casefold()
            != self.default_category.casefold()
        ]

        return [
            self.default_category,
            *categories
        ]


    def create_category(
        self,
        category
    ):
        """
        Crée un nouveau sous-répertoire
        de classement.
        """

        category = category.strip()

        if not category:
            category = (
                self.default_category
            )

        #
        # Un classement correspond à un seul
        # niveau de sous-répertoire.
        #
        category = re.sub(
            r'[\\/:*?"<>|]',
            "_",
            category
        )

        category = category.strip(
            " ."
        )

        if not category:
            category = (
                self.default_category
            )

        folder = (
            self.root
            / category
        )

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        return folder

    def trouver_projet_prepare(self, audio_file):
        """
        P18.6-bis (spec correctifs §19) : cherche un
        dossier projet où cet audio a DÉJÀ été
        prétraité lors d'une session précédente —
        copie de l'audio présente, audio finalisé
        (``audio_processed.wav``) et journal de
        prétraitement, SANS transcription
        (project.sttproj absent).

        Retour : chemin du dossier (la transcription
        directe de l'audio traité s'y poursuit), ou
        None.
        """

        from pathlib import Path as _Path

        source = _Path(audio_file)

        if not self.root or not source.name:
            return None

        for categorie in sorted(
            _Path(self.root).iterdir()
        ):

            if not categorie.is_dir():
                continue

            for dossier in sorted(
                categorie.iterdir()
            ):

                if not dossier.is_dir():
                    continue

                if not (
                    dossier / source.name
                ).is_file():
                    continue

                if not (
                    dossier
                    / "audio_processed.wav"
                ).is_file():
                    continue

                if not (
                    dossier
                    / "journal_operations.json"
                ).is_file():
                    continue

                if (
                    dossier
                    / "project.sttproj"
                ).is_file():
                    # Déjà transcrit : ce n'est pas un
                    # audio « en attente ».
                    continue

                return dossier

        return None

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

        category = (
            category.strip()
            if category
            else self.default_category
        )

        if not category:
            category = (
                self.default_category
            )

        base_folder = (
            self.create_category(
                category
            )
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

    def delete_provisional_project(
        self,
        project_folder,
        attempts=3,
        delay=0.15
    ):
        project_folder = Path(
            project_folder
        )

        if not project_folder.exists():
            return True

        last_error = None

        for attempt in range(
            attempts
        ):
            try:
                shutil.rmtree(
                    project_folder
                )
                return True

            except FileNotFoundError:
                return True

            except OSError as e:
                last_error = e

                if attempt < attempts - 1:
                    time.sleep(
                        delay
                    )

        if last_error is not None:
            raise last_error

        return False

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






    