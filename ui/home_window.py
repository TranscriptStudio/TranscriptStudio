from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
)
from PySide6.QtCore import (
    QThread,
    Qt,
    QSize,
)
from PySide6.QtGui import (
    QPixmap,
    QFont,
    QIcon,
    QPalette,
    QColor,
)

from pathlib import Path

from services.settings import SettingsManager
from services.api_capabilities import can_access_account_info, has_transcription_api
from ui.new_transcription_dialog import NewTranscriptionDialog
from ui.settings_dialog import SettingsDialog
from ui.elevenlabs_account_dialog import ElevenLabsAccountDialog
from ui.progress_dialog import ProgressDialog
from ui.main_window import MainWindow
from ui.transcription_entry_dialog import (TranscriptionEntryDialog)
from ui.audio_preprocess_dialog import (AudioPreprocessDialog)

from services.elevenlabs_transcriber import ElevenLabsTranscriber
from services.project_manager import ProjectManager
from services.elevenlabs_importer import import_elevenlabs_json
from services.help import open_user_manual
from services.project_io import load_project
from services.resources import resource_path
from services.transcription_worker import TranscriptionWorker
from services.project_io import save_project
from services.audio_loading_worker import AudioLoadingWorker

class HomeWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.settings = SettingsManager()
        self.transcription_thread = None
        self.transcription_worker = None
        self.progress_dialog = None
        self.transcription_started = False

        self.setWindowTitle(
            "Transcript Studio"
        )

        self.resize(
            550,
            500
        )

        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(10)

        # En-tete
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(14)

        icon_label = QLabel()
        pixmap = QPixmap(str(resource_path("icons/logo.png")))
        icon_label.setPixmap(
            pixmap.scaled(
                120,
                120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        self.title_label = QLabel("Transcript Studio")
        title_font = QFont("Segoe UI Light", 28)
        title_font.setWeight(QFont.Weight.Light)
        self.title_label.setFont(title_font)

        self.subtitle_label = QLabel(
            "Prétraitement audio et transcription assistée par ElevenLabs"
        )
        self.version_label = QLabel("Version 1.1\nSeptembre 2026")
        self.api_status_label = QLabel("")
        self.api_status_label.setStyleSheet("font-size: 12px; color: #666666;")

        # Les couleurs sont appliquees par une methode separee afin de pouvoir
        # les recalculer immediatement apres un changement de theme.
        self.update_header_colors()
        self.update_api_status()

        title_layout.addWidget(self.title_label)
        title_layout.addSpacing(4)
        title_layout.addWidget(self.subtitle_label)
        title_layout.addSpacing(8)
        title_layout.addWidget(self.version_label)
        title_layout.addSpacing(4)
        title_layout.addWidget(self.api_status_label)

        header_layout.addWidget(
            icon_label,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        layout.addSpacing(6)

        # Actions principales
        self.new_transcription_button = QPushButton("Nouvelle transcription")
        self.open_project_button = QPushButton("Ouvrir un projet")

        self.new_transcription_button.setIcon(
            QIcon(str(resource_path("icons/bubble-text.svg")))
        )
        self.open_project_button.setIcon(
            QIcon(str(resource_path("icons/folder-open.svg")))
        )

        self.new_transcription_button.setToolTip(
            "Créer une nouvelle transcription"
        )
        self.open_project_button.setToolTip(
            "Ouvrir un projet existant"
        )

        for button in (
            self.new_transcription_button,
            self.open_project_button,
        ):
            button.setFixedSize(200, 38)

        main_actions_layout = QHBoxLayout()
        main_actions_layout.setContentsMargins(0, 0, 0, 0)
        main_actions_layout.setSpacing(12)
        main_actions_layout.addStretch()
        main_actions_layout.addWidget(self.new_transcription_button)
        main_actions_layout.addWidget(self.open_project_button)
        main_actions_layout.addStretch()
        layout.addLayout(main_actions_layout)
        layout.addSpacing(6)

        # Projets recents
        recent_label = QLabel("Projets récents")
        layout.addWidget(recent_label)

        self.recent_projects = QListWidget()
        self.recent_projects.setMinimumHeight(160)

        for project in self.settings.cleanup_recent_projects():
            project_path = Path(project)
            project_name = project_path.parent.name
            category_name = project_path.parent.parent.name
            display_name = f"{category_name} ▸ {project_name}"

            item = QListWidgetItem(display_name)
            item.setData(
                Qt.ItemDataRole.UserRole,
                str(project_path),
            )
            item.setToolTip(str(project_path))
            self.recent_projects.addItem(item)

        self.recent_projects.itemDoubleClicked.connect(
            self.open_recent_project
        )

        layout.addWidget(
            self.recent_projects,
            stretch=1,
        )
        layout.addSpacing(10)

        # Actions secondaires
        self.settings_button = QPushButton("Paramètres")
        self.elevenlabs_button = QPushButton("Compte ElevenLabs")
        self.help_button = QPushButton("Manuel")

        self.settings_button.setIcon(
            QIcon(str(resource_path("icons/settings.svg")))
        )
        self.elevenlabs_button.setIcon(
            QIcon(str(resource_path("icons/user.svg")))
        )
        self.help_button.setIcon(
            QIcon(str(resource_path("icons/info-square-rounded.svg")))
        )

        self.settings_button.setToolTip("Configurer Transcript Studio")
        self.elevenlabs_button.setToolTip(
            "Afficher les informations du compte ElevenLabs"
        )
        self.help_button.setToolTip("Ouvrir le manuel utilisateur")

        for button in (
            self.settings_button,
            self.elevenlabs_button,
            self.help_button,
        ):
            button.setFixedSize(150, 36)

        bottom_actions_layout = QHBoxLayout()
        bottom_actions_layout.setContentsMargins(0, 0, 0, 0)
        bottom_actions_layout.setSpacing(10)
        bottom_actions_layout.addStretch()
        bottom_actions_layout.addWidget(self.settings_button)
        bottom_actions_layout.addWidget(self.elevenlabs_button)
        bottom_actions_layout.addWidget(self.help_button)
        bottom_actions_layout.addStretch()
        layout.addLayout(bottom_actions_layout)

        # Taille commune des icones
        button_icon_size = QSize(19, 19)
        for button in (
            self.new_transcription_button,
            self.open_project_button,
            self.settings_button,
            self.elevenlabs_button,
            self.help_button,
        ):
            button.setIconSize(button_icon_size)

        # Connexions
        self.new_transcription_button.clicked.connect(
            self.new_transcription
        )
        self.open_project_button.clicked.connect(
            self.open_project
        )
        self.settings_button.clicked.connect(
            self.open_settings
        )
        self.elevenlabs_button.clicked.connect(
            self.open_elevenlabs_account
        )
        self.help_button.clicked.connect(open_user_manual)


    def update_header_colors(self):
        theme = self.settings.get_theme()

        if theme == "dark":
            title_color = "#F0F0F0"
            subtitle_color = "#C0C0C0"
            version_color = "#A8A8A8"
        elif theme == "light":
            title_color = "#191919"
            subtitle_color = "#555555"
            version_color = "#777777"
        else:
            is_dark = (
                self.palette().window().color().lightness() < 128
            )
            if is_dark:
                title_color = "#F0F0F0"
                subtitle_color = "#C0C0C0"
                version_color = "#A8A8A8"
            else:
                title_color = "#191919"
                subtitle_color = "#555555"
                version_color = "#777777"

        self.title_label.setStyleSheet(
            f"color: {title_color}; font-size: 26px;"
        )
        self.subtitle_label.setStyleSheet(
            f"color: {subtitle_color}; font-size: 13px; font-weight: 400;"
        )
        self.version_label.setStyleSheet(
            f"color: {version_color}; font-size: 12px;"
        )


    def open_settings(self):
        dialog = SettingsDialog(self)
        result = dialog.exec()

        if result:
            self.settings.load()
            self.update_header_colors()
            self.update_api_status()
                
    def update_api_status(self):
        """Met à jour l'affichage de l'état de l'API de transcription."""
        if has_transcription_api():
            self.api_status_label.setText("Service de transcription : configuré")
        else:
            self.api_status_label.setText("Service de transcription : non configuré")
    def new_transcription(self):

        entry_dialog = (
            TranscriptionEntryDialog(
                self
            )
        )

        if not entry_dialog.exec():
            return

        result = (
            entry_dialog.get_result()
        )
        print(result)

        audio_file = (
            result["audio_file"]
        )

        mode = (
            result["mode"]
        )
        category = (
            result["category"]
        )
        manager = ProjectManager()

        project_folder = (
            manager.create_project_folder(
                audio_file,
                category
            )
        )

        project_audio_file = (
            manager.copy_audio_file(
                audio_file,
                project_folder
            )
        )

        self.current_project_folder = (
            project_folder
        )

        self.current_audio_file = (
            project_audio_file
        )

        if mode == (
            TranscriptionEntryDialog.MODE_DIRECT
        ):
            dialog = NewTranscriptionDialog(
                str(project_audio_file),
                self
            )

            if not dialog.exec():
                # Vérifier si l'utilisateur a demandé à ouvrir les paramètres
                if dialog.should_open_settings():
                    self.open_settings()
                
                try:
                    manager.delete_provisional_project(
                        project_folder
                    )

                except OSError as e:
                    QMessageBox.critical(
                        self,
                        "Erreur de nettoyage",
                        (
                            "Impossible de supprimer "
                            "le projet provisoire.\n\n"
                            + str(e)
                        )
                    )

                return

            options = dialog.get_options()

            self.start_transcription(
                project_audio_file,
                options
            )

            return
            
            
        if mode == (
            TranscriptionEntryDialog.MODE_PREPROCESSING
        ):
            self.start_audio_loading(
                project_audio_file,
                project_folder
            )

            return     

    def refresh_recent_projects(self):
        self.recent_projects.clear()

        for project in (
            self.settings.cleanup_recent_projects()
        ):
            project_path = Path(
                project
            )

            project_name = (
                project_path.parent.name
            )

            category_name = (
                project_path.parent.parent.name
            )

            display_name = (
                f"{category_name} ▸ {project_name}"
            )

            item = QListWidgetItem(
                display_name
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                str(project_path)
            )

            item.setToolTip(
                str(project_path)
            )

            self.recent_projects.addItem(
                item
            )

    def open_project(self):

        projects_root = (
            self.settings
            .get_projects_root()
        )

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un projet",
            projects_root,
            "Projet (*.sttproj)"
        )

        if not filename:
            return

        project = load_project(
            filename
        )

        self.editor = MainWindow(
            project
        )

        self.editor.show()

        self.close()

    def open_recent_project(
        self,
        item
    ):
        filename = item.data(
            Qt.ItemDataRole.UserRole
        )

        if not filename:
            return

        if not Path(
            filename
        ).exists():
            QMessageBox.warning(
                self,
                "Projet introuvable",
                (
                    "Le fichier\n\n"
                    f"{filename}\n\n"
                    "n'existe plus."
                )
            )
            return

        project = load_project(
            filename
        )

        self.editor = MainWindow(
            project
        )

        self.editor.show()

        self.close()

    def transcription_finished(
        self,
        data
    ):
        if self.progress_dialog is not None:
            self.progress_dialog.close()

        manager = ProjectManager()

        json_file = (
            manager.save_transcription_json(
                data,
                self.current_project_folder
            )
        )

        project = import_elevenlabs_json(
            str(json_file)
        )

        project.audio_file = str(
            self.current_audio_file
        )

        project.name = Path(
            self.current_audio_file
        ).stem

        project.project_file = str(
            self.current_project_folder
            / "project.sttproj"
        )

        save_project(
            project,
            project.project_file
        )

        self.settings.add_recent_project(
            project.project_file
        )

        self.refresh_recent_projects()

        self.editor = MainWindow(
            project
        )

        self.editor.show()
        self.close()

    def transcription_error(
        self,
        message
    ):
        if self.progress_dialog is not None:
            self.progress_dialog.close()

        QMessageBox.critical(
            self,
            "Erreur de transcription",
            message
        )

    def open_elevenlabs_account(self):

        if not can_access_account_info():
            QMessageBox.information(
                self,
                "Service non configuré",
                "Pour consulter les informations de votre compte ElevenLabs, "
                "vous devez d'abord configurer une clé API valide dans les paramètres."
            )
            return

        dialog = ElevenLabsAccountDialog(
            self
        )

        dialog.exec()

    def start_audio_loading(
        self,
        audio_file,
        project_folder
    ):
        #
        # Conserver les informations nécessaires
        # pour la suite du workflow.
        #
        self.loading_audio_file = (
            audio_file
        )

        self.loading_project_folder = (
            project_folder
        )

        #
        # Popup de chargement.
        #
        self.audio_loading_progress = (
            QProgressDialog(
                "Préparation du fichier audio en cours...\n"
                "Veuillez patienter.",
                "",
                0,
                0,
                self
            )
        )

        self.audio_loading_progress.setWindowTitle(
            "Chargement du fichier audio"
        )

        self.audio_loading_progress.setWindowModality(
            Qt.WindowModal
        )

        #
        # Pas de bouton Annuler pour l'instant.
        #
        self.audio_loading_progress.setCancelButton(
            None
        )

        #
        # Affichage immédiat.
        #
        self.audio_loading_progress.setMinimumDuration(
            0
        )

        #
        # 0, 0 = indicateur indéterminé.
        #
        self.audio_loading_progress.setRange(
            0,
            0
        )

        self.audio_loading_progress.setAutoClose(
            False
        )

        self.audio_loading_progress.setAutoReset(
            False
        )

        #
        # Thread.
        #
        self.audio_loading_thread = QThread(
            self
        )

        #
        # Worker.
        #
        self.audio_loading_worker = (
            AudioLoadingWorker(
                str(audio_file)
            )
        )

        self.audio_loading_worker.moveToThread(
            self.audio_loading_thread
        )

        #
        # Démarrage du travail.
        #
        self.audio_loading_thread.started.connect(
            self.audio_loading_worker.run
        )

        #
        # Fin correcte.
        #
        self.audio_loading_worker.finished.connect(
            self.audio_loading_finished
        )

        self.audio_loading_worker.finished.connect(
            self.audio_loading_thread.quit
        )

        #
        # Erreur.
        #
        self.audio_loading_worker.error.connect(
            self.audio_loading_error
        )

        self.audio_loading_worker.error.connect(
            self.audio_loading_thread.quit
        )

        #
        # Nettoyage du worker.
        #
        self.audio_loading_thread.finished.connect(
            self.audio_loading_worker.deleteLater
        )
        self.audio_loading_thread.finished.connect(
            self.cleanup_audio_loading
        )
        #
        # Afficher avant de démarrer.
        #
        self.audio_loading_progress.show()

        #
        # Démarrer le worker.
        #
        self.audio_loading_thread.start()

    def audio_loading_finished(
        self,
        audio_document
    ):
        #
        # Fermer le popup.
        #
        self.audio_loading_progress.close()

        audio_file = (
            self.loading_audio_file
        )

        project_folder = (
            self.loading_project_folder
        )

        #
        # Poursuivre le workflow.
        #
        self.open_audio_preprocess_dialog(
            audio_file,
            project_folder,
            audio_document
        )

    def open_audio_preprocess_dialog(
        self,
        audio_file,
        project_folder,
        audio_document
    ):
        preprocess_dialog = (
            AudioPreprocessDialog(
                str(audio_file),
                project_folder,
                audio_document=audio_document,
                parent=self
            )
        )

        if not preprocess_dialog.exec():
            return

        processed_audio_file = (
            preprocess_dialog
            .get_processed_audio_file()
        )

        if not processed_audio_file:
            QMessageBox.critical(
                self,
                "Fichier audio indisponible",
                (
                    "Le fichier audio finalisé "
                    "est introuvable.\n\n"
                    "La transcription ne peut pas "
                    "être poursuivie."
                )
            )
            return

        processed_audio_file = Path(
            processed_audio_file
        )

        if not processed_audio_file.exists():
            QMessageBox.critical(
                self,
                "Fichier audio introuvable",
                (
                    "Le fichier audio finalisé "
                    "n'existe plus :\n\n"
                    f"{processed_audio_file}"
                )
            )
            return

        self.current_audio_file = (
            processed_audio_file
        )
        
        # Vérifier le mode de finalisation sélectionné
        finalize_mode = preprocess_dialog.get_finalize_mode()
        
        # Si l'utilisateur a choisi de finaliser uniquement, ne pas ouvrir NewTranscriptionDialog
        if finalize_mode == "finalize_only":
            # Finalisation sans transcription - projet validé, pas de transcription
            print(
                "[WORKFLOW] Audio finalisé uniquement :",
                processed_audio_file
            )
            return
        
        # Mode transcription : ouvrir NewTranscriptionDialog
        print(
            "[WORKFLOW] Audio transmis à NewTranscriptionDialog :",
            processed_audio_file
        )
        dialog = NewTranscriptionDialog(
            str(processed_audio_file),
            self
        )
        
        if not dialog.exec():
            # Vérifier si l'utilisateur a demandé à ouvrir les paramètres
            if dialog.should_open_settings():
                self.open_settings()
            
            try:
                manager = ProjectManager()

                manager.delete_provisional_project(
                    project_folder
                )

            except OSError as e:
                QMessageBox.critical(
                    self,
                    "Erreur de nettoyage",
                    (
                        "Impossible de supprimer "
                        "le projet provisoire.\n\n"
                        + str(e)
                    )
                )

            return

        options = dialog.get_options()

        self.start_transcription(
            processed_audio_file,
            options
        )

    def audio_loading_error(
        self,
        message
    ):
        self.audio_loading_progress.close()

        self.audio_loading_progress = None
        self.audio_loading_thread = None
        self.audio_loading_worker = None

        QMessageBox.critical(
            self,
            "Erreur de chargement",
            (
                "Impossible de préparer "
                "le fichier audio.\n\n"
                + message
            )
        )

    def cleanup_audio_loading(
        self
    ):
        self.audio_loading_progress = None
        self.audio_loading_thread = None
        self.audio_loading_worker = None

    def start_transcription(
        self,
        audio_file,
        options
    ):
        if self.transcription_thread is not None:
            return

        audio_file = Path(
            audio_file
        )

        if not audio_file.exists():
            QMessageBox.critical(
                self,
                "Fichier audio introuvable",
                (
                    "Le fichier audio à transcrire "
                    "est introuvable.\n\n"
                    f"{audio_file}"
                )
            )
            return

        #
        # Dès cet instant, le projet ne doit
        # plus être considéré comme provisoire.
        #
        self.transcription_started = True

        self.current_audio_file = audio_file

        #
        # Fenêtre de progression existante.
        #
        self.progress_dialog = ProgressDialog(
            str(audio_file),
            self
        )

        self.progress_dialog.setWindowModality(
            Qt.WindowModal
        )

        #
        # Thread.
        #
        self.transcription_thread = QThread(
            self
        )

        self.transcription_worker = (
            TranscriptionWorker(
                str(audio_file),
                options
            )
        )

        self.transcription_worker.moveToThread(
            self.transcription_thread
        )

        #
        # Démarrage.
        #
        self.transcription_thread.started.connect(
            self.transcription_worker.run
        )

        #
        # Succès.
        #
        self.transcription_worker.finished.connect(
            self.transcription_finished
        )

        self.transcription_worker.finished.connect(
            self.transcription_thread.quit
        )

        #
        # Erreur.
        #
        self.transcription_worker.error.connect(
            self.transcription_error
        )

        self.transcription_worker.error.connect(
            self.transcription_thread.quit
        )

        #
        # Nettoyage Qt.
        #
        self.transcription_thread.finished.connect(
            self.transcription_worker.deleteLater
        )

        self.transcription_thread.finished.connect(
            self.cleanup_transcription
        )

        #
        # Afficher avant le démarrage.
        #
        self.progress_dialog.show()
        self.transcription_thread.start()

    def cleanup_transcription(
        self
    ):
        self.transcription_thread = None
        self.transcription_worker = None

