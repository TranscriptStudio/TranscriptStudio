from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFileDialog,
)

from services.settings import SettingsManager
from services.elevenlabs_transcriber import (
    ElevenLabsTranscriber
)
from services.help import (
    open_user_manual
)

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

        layout = QVBoxLayout(self)


        

        self.projects_root_edit = QLineEdit(
            self.settings.get_projects_root()
        )



        self.projects_root_button = QPushButton(
            "Parcourir..."
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
        # self.help_button = QPushButton(
        #     "Manuel utilisateur"
        # )
        self.save_button = QPushButton(
            "Enregistrer"
        )

        self.cancel_button = QPushButton(
            "Annuler"
        )
        # ordre des éléments

        layout.addWidget(
            QLabel(
                "Clé API ElevenLabs"
            )
        )
        layout.addWidget(
            self.api_key_edit
        )
        layout.addWidget(
                QLabel(
                    "Répertoire des projets"
                )
            )
        layout.addWidget(
            self.projects_root_edit
        )
        layout.addWidget(
            self.projects_root_button
        )


        # layout.addWidget(
        #     self.help_button
        # )

        layout.addWidget(
            self.test_button
        )

        layout.addWidget(
            self.save_button
        )

        layout.addWidget(
            self.cancel_button
        )

        # self.help_button.clicked.connect(
        #     open_user_manual
        # )
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









