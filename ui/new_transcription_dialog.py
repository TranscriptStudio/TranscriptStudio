from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QComboBox,
    QCheckBox,
    QMessageBox,
    QGroupBox,
)

from pathlib import Path
from services.api_capabilities import has_transcription_api

class NewTranscriptionDialog(QDialog):

    def __init__(
        self,
        audio_file,
        parent=None
    ):
        super().__init__(parent)

        self.audio_file = audio_file
        self._open_settings_requested = False

        self.setWindowTitle(
            "Nouvelle transcription"
        )

        self.resize(500, 300)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                f"Fichier : {Path(self.audio_file).name}"
            )
        )


        #
        # Langue
        #
        layout.addWidget(
            QLabel(
                "Langue de transcription"
            )
        )
        self.language_combo = QComboBox()

        self.language_combo.addItems([

            "Auto-détection",

            "fr - Français",
            "en - English",
            "es - Español",
            "de - Deutsch",
            "it - Italiano",
            "pt - Português",
            "nl - Nederlands",
        ])


        layout.addWidget(
            self.language_combo
        )

        #
        # Modèle
        #
        self.model_id_edit = QLineEdit(
            "scribe_v2"
        )

        layout.addWidget(
            QLabel(
                "Modèle ElevenLabs"
            )
        )

        layout.addWidget(
            QLabel(
                "Laisser 'scribe_v2' sauf si modèle spécifique ou mise à jour"
            )
        )

        layout.addWidget(
            self.model_id_edit
        )

        #
        # Options
        #
        options_group = QGroupBox(
        "Options de transcription"
        )
        
        options_layout = QVBoxLayout()
        self.diarize_checkbox = QCheckBox(
            "Diarisation"
        )
        self.diarize_checkbox.setChecked(True)
        self.diarize_checkbox.toggled.connect(
            self.update_diarization_options
        )

        self.no_verbatim_checkbox = QCheckBox(
            "Supprimer les hésitations et répétitions"
        )
        self.no_verbatim_checkbox.setChecked(True)

        self.speaker_library_checkbox = QCheckBox(
            "Reconnaissance des intervenants connus depuis la librarie elevenlabs (voir gestion sur site web)"
        )
        self.speaker_library_checkbox.setChecked(True)

        self.speaker_roles_checkbox = QCheckBox(
            "Détection automatique des rôles (surcoût de +10%)"
        )

        options_layout.addWidget(
            self.diarize_checkbox
        )

        options_layout.addWidget(
            self.no_verbatim_checkbox
        )

        options_layout.addWidget(
            self.speaker_library_checkbox
        )

        options_layout.addWidget(
            self.speaker_roles_checkbox
        )
        #
        # Mots-clés
        #
        self.keywords_edit = QLineEdit()

        self.keywords_edit.setPlaceholderText(
            "mot1, mot2, mot3 ..."
        )

        keywords_label = QLabel(
            "Mots-clés personnalisés (+20%)"
        )

        options_layout.addWidget(
            keywords_label
        )

        options_layout.addWidget(
            self.keywords_edit
        )   
        options_group.setLayout(
            options_layout
        )
        layout.addWidget(
            options_group
        )

        #
        # Boutons
        #
        self.transcribe_button = QPushButton(
            "Transcrire"
        )

        self.cancel_button = QPushButton(
            "Annuler"
        )

        layout.addWidget(
            self.transcribe_button
        )

        layout.addWidget(
            self.cancel_button
        )
        self.cancel_button.clicked.connect(
            self.request_cancel
        )
        self.transcribe_button.clicked.connect(
            self._handle_transcribe
        )
        self.update_diarization_options()
        self._update_transcribe_button_state()

    def confirm_cancel(self):
        reply = QMessageBox.question(
            self,
            "Abandonner la transcription",
            (
                "Abandonner cette transcription ?\n\n"
                "La réunion provisoire et ses fichiers "
                "seront supprimés."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No
        )

        return (
            reply
            == QMessageBox.StandardButton.Yes
        )

    def request_cancel(self):
        if not self.confirm_cancel():
            return

        self.reject()        

    def closeEvent(self, event):
        if self.confirm_cancel():
            event.accept()
        else:
            event.ignore()

    def _handle_transcribe(self):
        """
        Gère le clic sur le bouton Transcrire.
        Vérifie si l'API est disponible avant d'accepter.
        """
        if not has_transcription_api():
            reply = QMessageBox.question(
                self,
                "Clé API requise",
                "Pour lancer une transcription, vous devez configurer une clé API ElevenLabs valide.\n\n"
                "Voulez-vous ouvrir les paramètres pour la configurer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Signaler qu'il faut ouvrir les paramètres
                # On utilise un attribut pour communiquer avec l'appelant
                self._open_settings_requested = True
                self.reject()
            return
        
        self.accept()
    
    def _update_transcribe_button_state(self):
        """
        Met à jour l'état du bouton Transcrire en fonction
        de la disponibilité de l'API.
        """
        api_available = has_transcription_api()
        self.transcribe_button.setEnabled(api_available)
        
        if api_available:
            self.transcribe_button.setToolTip("")
        else:
            self.transcribe_button.setToolTip(
                "Clé API ElevenLabs requise. Configurez-la dans les paramètres pour activer la transcription."
            )
    
    def get_options(self):

        return {
            "audio_file":
                self.audio_file,

            "model_id":
                self.model_id_edit.text().strip(),

            "language_code":
                self.get_language_code(),

            "diarize":
                self.diarize_checkbox.isChecked(),

            "no_verbatim":
                self.no_verbatim_checkbox.isChecked(),

            "use_speaker_library":
                self.speaker_library_checkbox.isChecked(),

            "detect_speaker_roles":
                self.speaker_roles_checkbox.isChecked(),
            "keyterms": [
                x.strip()
                for x in self.keywords_edit.text().split(",")
                if x.strip()
            ],
        }
    
    def should_open_settings(self) -> bool:
        """Retourne True si l'utilisateur a demandé à ouvrir les paramètres."""
        return self._open_settings_requested
    
    def get_language_code(self):

        value = self.language_combo.currentText()

        if value == "Auto-détection":
            return None

        return value.split(" - ")[0]

    def update_diarization_options(self):

        enabled = self.diarize_checkbox.isChecked()

        self.speaker_library_checkbox.setEnabled(
            enabled
        )

        self.speaker_roles_checkbox.setEnabled(
            enabled
        )
        