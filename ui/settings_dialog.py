from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QComboBox,
    QApplication,
)
from PySide6.QtCore import (
    QSize,
)

from PySide6.QtGui import (
    QIcon,
)
from services.resources import resource_path
from services.settings import SettingsManager
from services.elevenlabs_transcriber import ElevenLabsTranscriber
from services.help import open_user_manual
from services.theme_manager import ThemeManager


class SettingsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = SettingsManager()

        self.setWindowTitle(
            "Paramètres"
        )

        self.resize(500, 200)

        self.build_ui()

    def build_ui(self):
        #
        # Layout principal
        #
        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            16,
            14,
            16,
            14
        )

        layout.setSpacing(
            12
        )

        #
        # ==================================================
        # Clé API ElevenLabs
        # ==================================================
        #
        api_label = QLabel(
            "Clé API ElevenLabs"
        )

        layout.addWidget(
            api_label
        )

        api_layout = QHBoxLayout()

        api_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        api_layout.setSpacing(
            8
        )

        self.api_key_edit = QLineEdit()

        self.api_key_edit.setText(
            self.settings.get_api_key()
        )

        self.api_key_edit.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        self.test_button = QPushButton(
            "Tester la connexion"
        )

        self.test_button.setFixedWidth(
            145
        )

        api_layout.addWidget(
            self.api_key_edit,
            1
        )

        api_layout.addWidget(
            self.test_button
        )

        layout.addLayout(
            api_layout
        )

        #
        # ==================================================
        # Répertoire des projets
        # ==================================================
        #
        projects_label = QLabel(
            "Répertoire des projets"
        )

        layout.addWidget(
            projects_label
        )

        projects_layout = QHBoxLayout()

        projects_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        projects_layout.setSpacing(
            8
        )

        self.projects_root_edit = QLineEdit(
            self.settings.get_projects_root()
        )

        self.projects_root_button = QPushButton(
            "Parcourir..."
        )

        self.projects_root_button.setIcon(
            QIcon(
                str(
                    resource_path(
                        "icons/folder-open.svg"
                    )
                )
            )
        )

        self.projects_root_button.setIconSize(
            QSize(
                18,
                18
            )
        )

        self.projects_root_button.setFixedWidth(
            115
        )

        projects_layout.addWidget(
            self.projects_root_edit,
            1
        )

        projects_layout.addWidget(
            self.projects_root_button
        )

        layout.addLayout(
            projects_layout
        )

        #
        # ==================================================
        # Thème de l'application
        # ==================================================
        #
        theme_layout = QHBoxLayout()

        theme_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        theme_layout.setSpacing(
            8
        )

        theme_label = QLabel(
            "Thème de l'application"
        )

        self.theme_combo = QComboBox()

        self.theme_combo.addItem(
            "Système",
            "system"
        )

        self.theme_combo.addItem(
            "Clair",
            "light"
        )

        self.theme_combo.addItem(
            "Sombre",
            "dark"
        )

        current_theme = (
            self.settings.get_theme()
        )

        index = self.theme_combo.findData(
            current_theme
        )

        if index >= 0:
            self.theme_combo.setCurrentIndex(
                index
            )

        #
        # Même largeur que les boutons de droite.
        #
        self.theme_combo.setFixedWidth(
            115
        )

        theme_layout.addWidget(
            theme_label
        )

        theme_layout.addStretch()

        theme_layout.addWidget(
            self.theme_combo
        )

        layout.addLayout(
            theme_layout
        )

        #
        # ==================================================
        # Actions
        # ==================================================
        #
        layout.addSpacing(
            4
        )

        self.cancel_button = QPushButton(
            "Annuler"
        )

        self.save_button = QPushButton(
            "Enregistrer"
        )

        self.cancel_button.setFixedSize(
            90,
            32
        )

        self.save_button.setFixedSize(
            90,
            32
        )

        buttons_layout = QHBoxLayout()

        buttons_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        buttons_layout.setSpacing(
            8
        )

        #
        # Actions alignées à droite.
        #
        buttons_layout.addStretch()

        buttons_layout.addWidget(
            self.cancel_button
        )

        buttons_layout.addWidget(
            self.save_button
        )

        layout.addLayout(
            buttons_layout
        )

        #
        # ==================================================
        # Connexions
        # ==================================================
        #
        self.save_button.clicked.connect(
            self.save_settings
        )

        self.cancel_button.clicked.connect(
            self.reject
        )

        self.test_button.clicked.connect(
            self.test_connection
        )

        self.projects_root_button.clicked.connect(
            self.select_projects_folder
        )        
    def save_settings(self):

        self.settings.set_api_key(
            self.api_key_edit.text().strip()
        )
        self.settings.set_projects_root(
            self.projects_root_edit.text()
        )


        theme = (
            self.theme_combo.currentData()
        )

        self.settings.set_theme(
            theme
        )

        app = QApplication.instance()

        if app is not None:
            ThemeManager.apply_theme(
                app,
                theme
            )
        self.accept()

    def test_connection(self):

        self.settings.set_api_key(
            self.api_key_edit.text().strip()
        )

        transcriber = (
            ElevenLabsTranscriber()
        )

        success, message = (
            transcriber.test_connection()
        )

        if success:

            QMessageBox.information(
                self,
                "Connexion réussie",
                message
            )

        else:

            QMessageBox.critical(
                self,
                "Erreur",
                message
            )

    def select_projects_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Choisir le répertoire projets"
        )

        if folder:

            self.projects_root_edit.setText(
                folder
            )









