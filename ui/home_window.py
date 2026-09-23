from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QLabel,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
)
from PySide6.QtCore import (
    QThread,
    Qt,
)
from PySide6.QtGui import (
    QPixmap,
    QFont,
)

from pathlib import Path

from services.settings import SettingsManager
from ui.new_transcription_dialog import NewTranscriptionDialog
from ui.settings_dialog import SettingsDialog
from ui.elevenlabs_account_dialog import ElevenLabsAccountDialog
from ui.progress_dialog import ProgressDialog
from ui.main_window import MainWindow
from ui.progress_dialog import ProgressDialog
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

        self.setWindowTitle(
            "Transcript Studio"
        )

        self.resize(
            700,
            500
        )

        self.build_ui()

    def build_ui(self):
        
        

        header_layout = QHBoxLayout()

        #
        # Icône
        #
        icon_label = QLabel()

        

        pixmap = QPixmap(str(resource_path("icons/logo.png")))  
            

        icon_label.setPixmap(
            pixmap.scaled(
                128,
                128,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

        #
        # Texte
        #
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        title_label = QLabel(
            "Transcript Studio"
        )
        title_font = QFont(
            "Segoe UI Light",
            28
        )

        title_font.setWeight(
            QFont.Weight.Light
        )
        title_label.setFont(
            title_font
        )
        title_label.setStyleSheet("""
            font-size:26px;
            font-weight:bold;
        """)
        subtitle_label = QLabel(
            "Transcription audio assistée par ElevenLabs"
        )

        subtitle_label.setStyleSheet("""
            color:#666666;
            font-size:12px;
        """)

        version_label = QLabel(
            "Version 1.0\nAoût 2026"
        )

        version_label.setStyleSheet("""
            color:#666666;
            font-size:12px;
        """)


        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        title_layout.addWidget(version_label)
        
        header_layout.addWidget(
            icon_label,
            alignment=Qt.AlignmentFlag.AlignVCenter
        )

        header_layout.addLayout(
            title_layout
        )

        header_layout.addStretch()
        layout = QVBoxLayout(self)
        layout.addLayout(
            header_layout
        )
        layout.addSpacing(10)

        self.help_button = QPushButton(
            "📖 Manuel"
        )
        self.elevenlabs_button = QPushButton(
            "👤 Compte ElevenLabs"
        )

        self.new_transcription_button = (
            QPushButton(
                "Nouvelle transcription"
            )
        )

        self.open_project_button = (
            QPushButton(
                "Ouvrir un projet"
            )
        )
        self.open_project_button.clicked.connect(
            self.open_project
        )
        self.recent_projects = QListWidget()
        self.settings_button = QPushButton(
            "Paramètres"
        )

        for project in (
            self.settings.get_recent_projects()
        ):
            self.recent_projects.addItem(
                project
            )
        self.recent_projects.itemDoubleClicked.connect(
            self.open_recent_project
        )

        layout.addWidget(
            self.new_transcription_button
        )

        layout.addWidget(
            self.open_project_button
        )

        layout.addWidget(
            QLabel("Projets récents")
        )

        layout.addWidget(
            self.recent_projects
        )
        self.new_transcription_button.clicked.connect(
            self.new_transcription
        )
        layout.addWidget(
            self.settings_button
        )
        layout.addWidget(
            self.elevenlabs_button
        )
        layout.addWidget(
            self.help_button
        )
        self.settings_button.clicked.connect(
            self.open_settings
        )     
        self.help_button.clicked.connect(
            open_user_manual
        )
        self.elevenlabs_button.clicked.connect(
            self.open_elevenlabs_account
        )

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
                return

            options = dialog.get_options()

            print(options)

            return
            
        if mode == (
            TranscriptionEntryDialog.MODE_PREPROCESSING
        ):
            self.start_audio_loading(
                project_audio_file,
                project_folder
            )

            return     
        
    def open_settings(self):

        dialog = SettingsDialog(
            self
        )

        dialog.exec()

    def refresh_recent_projects(self):

        self.recent_projects.clear()

        for project in (
            self.settings.get_recent_projects()
        ):

            if Path(project).exists():

                self.recent_projects.addItem(
                    project
                )

    def open_project(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un projet",
            "",
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

    def open_recent_project(self, item):

        filename = item.text()

        if not Path(filename).exists():

            QMessageBox.warning(
                self,
                "Projet introuvable",
                f"Le fichier\n\n{filename}\n\nn'existe plus."
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
        
        self.editor = MainWindow(project)
        
        self.editor.show()

        self.close()

    def transcription_error(
        self,
        message
    ):

        self.progress_dialog.close()

        QMessageBox.critical(
            self,
            "Erreur de transcription",
            message
        )

    def open_elevenlabs_account(self):

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
            return

        self.current_audio_file = (
            Path(
                processed_audio_file
            )
        )

        dialog = NewTranscriptionDialog(
            processed_audio_file,
            self
        )

        if not dialog.exec():
            return

        options = dialog.get_options()

        print(options)


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

