import json
from pathlib import Path
from PySide6.QtCore import QStandardPaths
from services.app_paths import (
    APP_DATA_DIR,
    LEGACY_PROJECTS_DIR,
)

class SettingsManager:

    def __init__(self, app_folder=None):

        # Dossier de parametrage injectable
        # (utilise par les tests pour isoler
        # la configuration reelle de l'utilisateur).
        self.app_folder = (
            Path(app_folder)
            if app_folder is not None
            else APP_DATA_DIR
        )

        self.app_folder.mkdir(
            parents=True,
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

            "recent_etudes": [],

            "theme": "system",

            "llm": {
                # Paramétrage LLM v2 (P15) :
                # sélection mémorisée app-wide ; chaque
                # étude peut surcharger (contrat format
                # étude §10).
                "fournisseur": "openai",
                "modele": "gpt-4.1",
                "temperature": 0.3,
                "max_tokens": None,
                "effort_raisonnement": None,
                # Températures par défaut par bloc
                # (décision C2 du 2026-10-27) :
                # reformulation 0.3 (sobre et fidèle),
                # résumé 0.2 ; surchargeables par étude
                # dans parametres.json.
                "temperatures": {
                    "reformulation": 0.3,
                    "resume": 0.2,
                },
            },
            
            "transcription_defaults": {

                "model_id": "scribe_v2","language_code": "fr",

                "diarize": True,

                "no_verbatim": True,

                "use_speaker_library": True,

                "detect_speaker_roles": False

            },
            "reformulation": {
                # P16-bis : page Reformulation — taille
                # du texte (défaut abaissé pour la lecture
                # en double colonne) et largeurs de
                # colonnes mémorisées (locuteurs, texte
                # brut, pastilles ; la colonne reformulée
                # absorbe l'espace restant).
                "taille_texte": 11,
                "largeur_locuteurs": 130,
                "largeur_brute": None,
                "largeur_pastilles": 160,
            },

            "projects_root": "",
            "initial_setup_completed": False,
        }
    
    def get_default_projects_root(self) -> str:
        """
        Retourne le chemin par defaut pour le repertoire projets.
        Utilise le dossier Documents natif de l'OS + /Projets Transcript Studio
        """
        try:
            # Obtenir le dossier Documents natif
            docs_path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
            if docs_path:
                return str(Path(docs_path) / "Projets Transcript Studio")
        except Exception:
            pass
        
        # Fallback : utiliser l'ancien emplacement pour compatibilite
        return str(LEGACY_PROJECTS_DIR)

    def get_api_key(self):

        return self.settings.get(
            "elevenlabs_api_key",
            ""
        )

    def is_initial_setup_completed(self) -> bool:
        """
        Verifie si la configuration initiale a ete validee.
        Retourne True si l'utilisateur a deja valide un repertoire projets.
        """
        return self.settings.get("initial_setup_completed", False)

    def set_initial_setup_completed(self, completed: bool) -> None:
        """
        Definit l'etat de la configuration initiale.
        Ne doit etre appele qu'apres validation reussie du repertoire projets.
        """
        self.settings["initial_setup_completed"] = completed
        self.save()

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

    def remove_recent_project(
        self,
        project_path
    ):
        """
        Retire un projet de la liste des projets
        recents. Le projet lui-meme n'est pas
        touche sur le disque.
        """

        projects = (
            self.get_recent_projects()
        )

        project_path = str(
            Path(project_path)
        )

        remaining_projects = [
            project
            for project in projects
            if project != project_path
        ]

        self.settings[
            "recent_projects"
        ] = remaining_projects

        self.save()

        return (
            len(remaining_projects)
            != len(projects)
        )

    def get_recent_etudes(self):
        """
        Liste des dossiers d'étude récents.
        """

        return self.settings.get(
            "recent_etudes",
            []
        )

    def add_recent_etude(
        self,
        etude_folder
    ):
        """
        Ajoute un dossier d'étude en tête des
        études récentes. L'étude elle-même n'est
        pas touchée sur le disque.
        """

        etudes = (
            self.settings.setdefault(
                "recent_etudes",
                []
            )
        )

        etude_folder = str(
            Path(etude_folder)
        )

        if etude_folder in etudes:

            etudes.remove(
                etude_folder
            )

        etudes.insert(
            0,
            etude_folder
        )

        self.settings[
            "recent_etudes"
        ] = etudes[:20]

        self.save()

    def remove_recent_etude(
        self,
        etude_folder
    ):
        """
        Retire une étude de la liste des études
        récentes. Le dossier étude n'est pas
        touché sur le disque.
        """

        etudes = (
            self.get_recent_etudes()
        )

        etude_folder = str(
            Path(etude_folder)
        )

        remaining_etudes = [
            etude
            for etude in etudes
            if etude != etude_folder
        ]

        self.settings[
            "recent_etudes"
        ] = remaining_etudes

        self.save()

        return (
            len(remaining_etudes)
            != len(etudes)
        )

    def cleanup_recent_etudes(self):
        """
        Supprime de la liste des études récentes
        les dossiers qui n'existent plus ou ne
        sont plus des études (etude.json absent).
        """

        etudes = (
            self.get_recent_etudes()
        )

        existing_etudes = [
            etude
            for etude in etudes
            if (
                Path(etude).is_dir()
                and (Path(etude) / "etude.json").is_file()
            )
        ]

        if existing_etudes != etudes:
            self.settings[
                "recent_etudes"
            ] = existing_etudes

            self.save()

        return existing_etudes

    def get_llm_config(self):
        """
        Paramétrage LLM mémorisé (P15) :
        fournisseur, modèle, température, max_tokens,
        effort de raisonnement. Chaque étude peut
        surcharger cette sélection.
        """

        llm = self.settings.get("llm", {})

        defaults = (
            self.default_settings()["llm"]
        )

        for cle, valeur in defaults.items():

            if cle not in llm:
                llm[cle] = valeur

        return llm

    def set_llm_config(self, config: dict) -> None:
        """
        Mémorise le paramétrage LLM (sélection
        app-wide ; les clés API ne passent jamais
        ici : elles vivent dans le CredentialStore).
        """

        self.settings["llm"] = dict(config)

        self.save()

    def get_reformulation_prefs(self):
        """
        Préférences de la page Reformulation (P16-bis) :
        taille du texte et largeurs de colonnes
        mémorisées. Les clés absentes (études de
        configurations antérieures) prennent les
        valeurs par défaut.
        """

        prefs = self.settings.get(
            "reformulation",
            {}
        )

        defaults = (
            self.default_settings()
            ["reformulation"]
        )

        for cle, valeur in defaults.items():

            if cle not in prefs:
                prefs[cle] = valeur

        return prefs

    def set_reformulation_prefs(self, prefs: dict):
        """
        Mémorise les préférences de la page
        Reformulation (fusion : seules les clés
        fournies sont mises à jour).
        """

        actuelles = self.settings.get(
            "reformulation",
            {}
        )

        actuelles.update(prefs)

        self.settings["reformulation"] = actuelles

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
            str(LEGACY_PROJECTS_DIR)
        )

    def set_projects_root(
        self,
        folder
    ):

        self.settings[
            "projects_root"
        ] = str(folder)

        self.save()

    def cleanup_recent_projects(self):
        """
        Supprime de la liste des projets récents
        les fichiers qui n'existent plus.
        """

        projects = (
            self.get_recent_projects()
        )

        existing_projects = [
            project
            for project in projects
            if Path(project).is_file()
        ]

        if existing_projects != projects:
            self.settings[
                "recent_projects"
            ] = existing_projects

            self.save()

        return existing_projects

    def get_theme(self):
        return self.settings.get(
            "theme",
            "system"
        )


    def set_theme(
            self,
            theme
        ):
            if theme not in {
                "system",
                "light",
                "dark",
            }:
                theme = "system"

            self.settings[
                "theme"
            ] = theme

            self.save()
    
    # P8 : Configuration utilisateur pour FFmpeg
    def get_ffmpeg_path(self):
        """
        Récupère le chemin FFmpeg personnalisé configured par l'utilisateur.
        
        Returns:
            str: Chemin personnalisé si configuré, None sinon
        """
        return self.settings.get("ffmpeg_path", None)
    
    def set_ffmpeg_path(self, path):
        """
        Définit le chemin FFmpeg personnalisé.
        
        Args:
            path: Chemin vers l'executable FFmpeg
        """
        self.settings["ffmpeg_path"] = str(path) if path else None
        self.save()






