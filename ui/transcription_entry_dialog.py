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
    QInputDialog,
)

from services.media_formats import (
    build_media_filter,
    is_video_file,
)
from services.project_manager import (
    ProjectManager
)
from services.api_capabilities import has_transcription_api

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

        self.project_manager = (
            ProjectManager()
        )

        self.setWindowTitle(
            "Nouvelle transcription"
        )

        self.resize(
            700,
            220
        )

        self.setModal(
            True
        )

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

        #
        # Sous-répertoire projet
        #
        category_group = QGroupBox(
            "Sous-répertoire du projet"
        )

        category_layout = QHBoxLayout(
            category_group
        )

        self.category_combo = (
            QComboBox()
        )

        self.category_combo.setEditable(
            False
        )

        self.new_category_button = (
            QPushButton(
                "Nouveau..."
            )
        )

        self.new_category_button.setToolTip(
            "Créer un nouveau sous-répertoire "
            "pour classer le projet"
        )

        category_layout.addWidget(
            self.category_combo,
            1
        )

        category_layout.addWidget(
            self.new_category_button
        )

        main_layout.addWidget(
            category_group
        )

        self.new_category_button.clicked.connect(
            self._create_category
        )

        self._refresh_categories()

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

    def _refresh_categories(
        self,
        selected_category=None
    ):
        """
        Recharge la liste des sous-répertoires
        existants.
        """

        if selected_category is None:
            selected_category = (
                self.category_combo
                .currentText()
                .strip()
            )

        categories = (
            self.project_manager
            .get_categories()
        )

        self.category_combo.blockSignals(
            True
        )

        self.category_combo.clear()

        self.category_combo.addItems(
            categories
        )

        if (
            selected_category
            and selected_category
            in categories
        ):
            self.category_combo.setCurrentText(
                selected_category
            )
        else:
            self.category_combo.setCurrentText(
                self.project_manager
                .default_category
            )

        self.category_combo.blockSignals(
            False
        )

    def _create_category(self):
        """
        Demande le nom d'un nouveau
        sous-répertoire puis le crée.
        """

        category, ok = (
            QInputDialog.getText(
                self,
                "Nouveau sous-répertoire",
                "Nom du sous-répertoire :"
            )
        )

        if not ok:
            return

        category = (
            category.strip()
        )

        if not category:
            return

        try:
            folder = (
                self.project_manager
                .create_category(
                    category
                )
            )

        except OSError as e:
            QMessageBox.critical(
                self,
                "Erreur de création",
                (
                    "Impossible de créer "
                    "le sous-répertoire.\n\n"
                    + str(e)
                )
            )
            return

        #
        # Recharge immédiatement la liste
        # et sélectionne le répertoire créé.
        #
        self._refresh_categories(
            folder.name
        )

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

        # Si le mode direct est sélectionné mais que l'API n'est pas disponible,
        # basculer automatiquement sur le prétraitement
        if self.direct_radio.isChecked() and not has_transcription_api():
            QMessageBox.information(
                self,
                "Service de transcription non configuré",
                "Une clé API ElevenLabs est nécessaire pour la transcription directe.\n\n"
                "Le projet sera créé en mode prétraitement pour une transcription ultérieure."
            )
            self.preprocessing_radio.setChecked(True)
            self.direct_radio.setChecked(False)

        if is_video_file(path):
            self.preprocessing_radio.setChecked(
                True
            )

            self.direct_radio.setChecked(
                False
            )

        self.accept()

    def _update_direct_radio_tooltip(self, is_video: bool):
        """Met à jour le tooltip du bouton radio de transcription directe."""
        if is_video:
            self.direct_radio.setToolTip(
                "La transcription directe est "
                "désactivée pour les vidéos. "
                "La piste audio doit d'abord "
                "être extraite."
            )
        else:
            if not has_transcription_api():
                self.direct_radio.setToolTip(
                    "Une clé API ElevenLabs est requise pour la transcription directe. "
                    "Configurez-la dans les paramètres."
                )
            else:
                self.direct_radio.setToolTip("")

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
            not video_selected and has_transcription_api()
        )

        self.video_info_label.setVisible(
            video_selected
        )

        self._update_direct_radio_tooltip(video_selected)
