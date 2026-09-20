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


class NewTranscriptionDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            "Nouvelle transcription"
        )

        self.resize(500, 300)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        #
        # Fichier audio
        #
        layout.addWidget(
            QLabel(
                "Fichier audio à transcrire"
            )
        )
        audio_layout = QHBoxLayout()

        self.audio_path = QLineEdit()

        self.browse_button = QPushButton(
            "Parcourir"
        )

        audio_layout.addWidget(
            self.audio_path
        )

        audio_layout.addWidget(
            self.browse_button
        )

        layout.addLayout(
            audio_layout
        )

        #
        # Sous-répertoire projet
        #
        layout.addWidget(
            QLabel(
                "Sous-répertoire du projet"
            )
        )
        self.category_combo = QComboBox()

        self.category_combo.setEditable(True)

        self.category_combo.addItems([
            "",
            "Commun",
        ])

        layout.addWidget(
            self.category_combo
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

        self.browse_button.clicked.connect(
            self.select_audio
        )

        self.transcribe_button.clicked.connect(
            self.validate_and_accept
        )

        self.cancel_button.clicked.connect(
            self.reject
        )
        self.update_diarization_options()


    def select_audio(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un audio",
            "",
            "Audio (*.mp3 *.wav *.m4a)"
        )

        if filename:
            self.audio_path.setText(
                filename
            )

    def get_options(self):

        return {
            "audio_file":
                self.audio_path.text(),

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
            "category":
                 self.category_combo.currentText().strip(),
        }
    
    def validate_and_accept(self):

        if not self.audio_path.text():

            QMessageBox.warning(
                self,
                "Audio manquant",
                "Veuillez sélectionner un fichier audio."
            )

            return

        self.accept()

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
        