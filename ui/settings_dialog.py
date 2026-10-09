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
    Qt,
)
from PySide6.QtGui import (
    QIcon,
    QCloseEvent,
)
from services.resources import resource_path
from services.settings import SettingsManager
from services.credential_store import CredentialStore
from services.elevenlabs_transcriber import ElevenLabsTranscriber
from services.help import open_user_manual
from services.theme_manager import ThemeManager


class SettingsDialog(QDialog):

    def __init__(self, parent=None, first_run=False):
        super().__init__(parent)

        self.settings = SettingsManager()
        self._credential_store = CredentialStore(self.settings.app_folder / "settings.json")
        self._is_first_run = first_run

        # En mode first-run, le titre est different et le comportement aussi
        if self._is_first_run:
            self.setWindowTitle("Bienvenue dans Transcript Studio - Configuration initiale")
        else:
            self.setWindowTitle("Paramètres")

        self.resize(500, 250)

        self.build_ui()
        
        # En mode first-run, on desactive le bouton Annuler et on le renomme Quitter
        if self._is_first_run:
            self.cancel_button.setText("Quitter")
            self.cancel_button.setToolTip("Quitter Transcript Studio")
    
    def validate_projects_root(self) -> tuple[bool, str]:
        """
        Valide le repertoire projets.
        Retourne (valide, message_erreur) ou (True, "") si OK.
        """
        from pathlib import Path
        
        projects_root = self.projects_root_edit.text().strip()
        
        # Verifier non vide
        if not projects_root:
            return False, "Le répertoire projets est obligatoire. Veuillez sélectionner un répertoire."
        
        # Verifier que c'est un repertoire (ou creable)
        path = Path(projects_root)
        
        # Si le chemin existe, verifier que c'est un repertoire
        if path.exists():
            if not path.is_dir():
                return False, f"Le chemin '{projects_root}' existe mais n'est pas un repertoire."
        else:
            # Le repertoire n'existe pas, essayer de le creer
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                return False, f"Impossible de creer le repertoire '{projects_root}': {e}"
        
        # Verifier les droits d'ecriture
        test_file = path / ".transcript_studio_test"
        try:
            test_file.write_text("test")
            test_file.unlink()  # Supprimer le fichier de test
        except OSError as e:
            return False, f"Pas de droits d'ecriture dans '{projects_root}': {e}"
        
        return True, ""
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Intercepter la fermeture de la fenetre.
        En mode first-run, on quitte l'application si l'utilisateur ferme.
        """
        if self._is_first_run:
            # En mode first-run, fermer la fenetre = quitter l'application
            QApplication.instance().quit()
            event.accept()
        else:
            # Comportement normal : accepter la fermeture
            event.accept()
    
    def quit_application(self):
        """
        Quitte l'application entiere.
        Utilise en mode first-run quand l'utilisateur clique sur Quitter.
        """
        QApplication.instance().quit()

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

        # Message d'introduction en mode first-run
        if self._is_first_run:
            intro_label = QLabel(
                "<b>Configuration initiale requise</b><br><br>"
                "Veuillez configurer le répertoire où vos projets seront enregistrés.<br>"
                "La clé API ElevenLabs est facultative et peut être ajoutée ultérieurement.<br><br>"
                "<i>Cette configuration ne peut pas être ignorée.</i>"
            )
            intro_label.setWordWrap(True)
            intro_label.setStyleSheet("color: #555;")
            layout.addWidget(intro_label)
            layout.addSpacing(20)
        
        #
        # ==================================================
        # Clé API ElevenLabs
        # ==================================================
        #
        api_label = QLabel(
            "Clé API ElevenLabs (facultative)"
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
            _credential_store.get_api_key()
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
        if self._is_first_run:
            projects_label = QLabel(
                "Répertoire des projets <span style='color: #D32F2F;'>*</span>"
            )
        else:
            projects_label = QLabel(
                "Répertoire des projets"
            )
        projects_label.setWordWrap(True)

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

        # En mode first-run, on part d'un champ vide pour forcer la selection
        if self._is_first_run:
            self.projects_root_edit = QLineEdit("")
        else:
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

        # En mode first-run, le bouton Quitter doit quitter l'application
        # Sinon, le bouton Annuler ferme juste le dialogue
        if self._is_first_run:
            self.cancel_button.clicked.connect(self.quit_application)
        else:
            self.cancel_button.clicked.connect(self.reject)

        self.test_button.clicked.connect(
            self.test_connection
        )

        self.projects_root_button.clicked.connect(
            self.select_projects_folder
        )        
    def save_settings(self):

        # En mode first-run, on valide que le repertoire projets est valide
        if self._is_first_run:
            is_valid, error_msg = self.validate_projects_root()
            if not is_valid:
                QMessageBox.critical(
                    self,
                    "Repertoire invalide",
                    error_msg
                )
                return  # Ne pas fermer le dialogue, l'utilisateur doit corriger
        
        # Sauvegarder les parametres
        _credential_store.set_api_key(
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

        # En mode first-run, marquer la configuration comme terminee
        if self._is_first_run:
            self.settings.set_initial_setup_completed(True)

        app = QApplication.instance()

        if app is not None:
            ThemeManager.apply_theme(
                app,
                theme
            )
        self.accept()

    def test_connection(self):

        _credential_store.set_api_key(
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
        from PySide6.QtCore import QStandardPaths
        from pathlib import Path
        
        # Definir le repertoire par defaut pour le dialogue
        default_dir = str(Path(QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)) / "TranscriptStudio Projects")
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choisir le répertoire projets",
            default_dir
        )

        if folder:

            self.projects_root_edit.setText(
                folder
            )









