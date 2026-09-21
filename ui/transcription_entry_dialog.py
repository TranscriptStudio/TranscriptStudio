# ui/transcription_entry_dialog.py

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QRadioButton,
    QMessageBox,
)


SUPPORTED_AUDIO_FILTER = (
    "Médias supportés (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus "
    "*.mp4 *.mov *.mkv *.avi *.webm);;"
    "Tous les fichiers (*.*)"
)


class TranscriptionEntryDialog(QDialog):
    """
    Première étape du workflow V1.1

    Sélection du fichier audio/vidéo.

    Puis choix :
        - Prétraitement audio
        - Transcription directe
    """

    MODE_PREPROCESSING = "preprocessing"

    MODE_DIRECT = "direct"

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Nouvelle transcription")

        self.resize(700, 220)

        self.setModal(True)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):

        main_layout = QVBoxLayout(self)

        title = QLabel(
            "Sélectionnez le média à utiliser pour la transcription"
        )

        title.setStyleSheet(
            "font-size:14px;font-weight:bold;"
        )

        main_layout.addWidget(title)

        # --------------------------------------------------------------
        # Fichier
        # --------------------------------------------------------------

        file_group = QGroupBox("Fichier audio ou vidéo")

        file_layout = QHBoxLayout(file_group)

        self.file_edit = QLineEdit()

        self.file_edit.setReadOnly(True)

        browse_btn = QPushButton("Parcourir...")

        browse_btn.clicked.connect(
            self._browse_file
        )

        file_layout.addWidget(self.file_edit)

        file_layout.addWidget(browse_btn)

        main_layout.addWidget(file_group)

        # --------------------------------------------------------------
        # Choix workflow
        # --------------------------------------------------------------

        mode_group = QGroupBox("Que souhaitez-vous faire ?")

        mode_layout = QVBoxLayout(mode_group)

        self.preprocessing_radio = QRadioButton(
            "Préparer et optimiser l'audio avant transcription"
        )

        self.direct_radio = QRadioButton(
            "Transcrire directement avec ElevenLabs"
        )

        self.preprocessing_radio.setChecked(True)

        mode_layout.addWidget(
            self.preprocessing_radio
        )

        mode_layout.addWidget(
            self.direct_radio
        )

        main_layout.addWidget(mode_group)

        # --------------------------------------------------------------
        # Boutons
        # --------------------------------------------------------------

        buttons_layout = QHBoxLayout()

        buttons_layout.addStretch()

        cancel_btn = QPushButton("Annuler")

        continue_btn = QPushButton("Continuer")

        cancel_btn.clicked.connect(
            self.reject
        )

        continue_btn.clicked.connect(
            self._validate
        )

        buttons_layout.addWidget(cancel_btn)

        buttons_layout.addWidget(continue_btn)

        main_layout.addLayout(buttons_layout)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_file(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un média",
            "",
            SUPPORTED_AUDIO_FILTER,
        )

        if filename:

            self.file_edit.setText(filename)

    def _validate(self):

        path = self.file_edit.text().strip()

        if not path:

            QMessageBox.warning(
                self,
                "Fichier manquant",
                "Veuillez sélectionner un fichier.",
            )

            return

        if not Path(path).exists():

            QMessageBox.warning(
                self,
                "Fichier introuvable",
                "Le fichier sélectionné n'existe pas.",
            )

            return

        self.accept()

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def get_audio_file(self) -> str:

        return self.file_edit.text().strip()

    def get_mode(self) -> str:

        if self.preprocessing_radio.isChecked():

            return self.MODE_PREPROCESSING

        return self.MODE_DIRECT

    def get_result(self) -> dict:

        return {
            "audio_file": self.get_audio_file(),
            "mode": self.get_mode(),
        }