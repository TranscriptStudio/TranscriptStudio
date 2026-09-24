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
    QComboBox,
)

from services.media_formats import (
    build_media_filter,
    is_video_file,
)

SUPPORTED_MEDIA_FILTER = (
    build_media_filter()
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

        self.file_edit.textChanged.connect(
            self._update_media_mode
        )

        self.file_edit.setReadOnly(True)

        browse_btn = QPushButton("Parcourir...")

        browse_btn.clicked.connect(
            self._browse_file
        )

        file_layout.addWidget(self.file_edit)

        file_layout.addWidget(browse_btn)

        main_layout.addWidget(file_group)

        self.video_info_label = QLabel(
            "Le fichier sélectionné est une vidéo. "
            "La piste audio sera extraite et convertie "
            "avant transcription."
        )

        self.video_info_label.setWordWrap(
            True
        )

        self.video_info_label.setStyleSheet("""
            QLabel {
                color: palette(mid);
                padding: 4px;
            }
        """)

        self.video_info_label.setVisible(
            False
        )

        main_layout.addWidget(
            self.video_info_label
        )

        # --------------------------------------------------------------
        # Sous-répertoire projet
        # --------------------------------------------------------------
        category_group = QGroupBox(
            "Sous-répertoire du projet"
        )
        category_layout = QVBoxLayout(
            category_group
        )

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems([
            "",
            "Commun",
        ])

        category_layout.addWidget(
            self.category_combo
        )

        main_layout.addWidget(
            category_group
        )

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
            SUPPORTED_MEDIA_FILTER,
        )

        if filename:
            self.file_edit.setText(
                filename
            )

            self._update_media_mode(
                filename
            )

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

        if is_video_file(path):
            self.preprocessing_radio.setChecked(
                True
            )

            self.direct_radio.setChecked(
                False
            )

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
            "category": (
                self.category_combo
                .currentText()
                .strip()
            ),
        }

    def _update_media_mode(
        self,
        filename
    ):
        video_extensions = {
            ".mp4",
            ".mov",
            ".mkv",
            ".avi",
            ".webm",
            ".mpeg",
            ".mpg",
            ".ts",
            ".m2ts",
        }

        extension = (
            Path(filename)
            .suffix
            .lower()
        )

        is_video = (
            extension
            in video_extensions
        )

        if is_video:
            self.preprocessing_radio.setChecked(
                True
            )

        self.direct_radio.setEnabled(
            not is_video
        )

    def _update_media_mode(
        self,
        filename
    ):
        video_selected = (
            is_video_file(
                filename
            )
        )

        if video_selected:
            #
            # Une vidéo doit obligatoirement
            # passer par le prétraitement afin
            # d'en extraire une piste audio.
            #
            self.preprocessing_radio.setChecked(
                True
            )

            self.direct_radio.setChecked(
                False
            )

        self.direct_radio.setEnabled(
            not video_selected
        )

        self.video_info_label.setVisible(
            video_selected
        )

        if video_selected:
            self.direct_radio.setToolTip(
                "La transcription directe est "
                "désactivée pour les vidéos. "
                "La piste audio doit d'abord "
                "être extraite."
            )
        else:
            self.direct_radio.setToolTip(
                ""
            )



