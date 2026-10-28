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
    QTabWidget,
    QWidget,
    QDoubleSpinBox,
    QSpinBox,
    QFormLayout,
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
from services.llm.catalogue import (
    CatalogueError,
    catalogue_par_defaut,
    charger_catalogue,
    reglages_affichables,
)
from services.llm.client import (
    ErreurLLM,
    creer_client,
)
from ui.catalogue_llm_dialog import CatalogueLLMDialog


class SettingsDialog(QDialog):

    def __init__(self, parent=None, first_run=False, settings=None):
        super().__init__(parent)

        #
        # Réglages injectables (P16-bis 3ᵉ série :
        # les tests isolent la configuration réelle
        # de l'utilisateur).
        #
        self.settings = (
            settings
            if settings is not None
            else SettingsManager()
        )
        self._credential_store = CredentialStore(self.settings.app_folder / "settings.json")
        self._is_first_run = first_run

        # Catalogue LLM (P15) : embarqué ou édité par
        # l'utilisateur dans le dossier de paramétrage.
        self._catalogue_llm = None
        self._ancien_fournisseur_id = None

        #
        # P16-bis (retour relecture §17) : résultat
        # du test de clé mémorisé par fournisseur —
        # changer de fournisseur et revenir ne perd
        # plus « Clé valide. » / « Clé invalide. ».
        #
        self._statuts_test = {}

        self._charger_catalogue_llm()

        # En mode first-run, le titre est different et le comportement aussi
        if self._is_first_run:
            self.setWindowTitle("Bienvenue dans Transcript Studio - Configuration initiale")
        else:
            self.setWindowTitle("Paramètres")

        self.resize(540, 480)

        self.build_ui()
        
        # En mode first-run, on desactive le bouton Annuler et on le renomme Quitter
        if self._is_first_run:
            self.cancel_button.setText("Quitter")
            self.cancel_button.setToolTip("Quitter Transcript Studio")
    
    def validate_projects_root(self) -> tuple[bool, str]:
        import os
        from pathlib import Path

        folder = self.projects_root_edit.text().strip()

        if not folder:
            return False, "Veuillez sélectionner un répertoire pour vos réunions."

        folder_path = Path(folder)

        # Créer le répertoire s'il n'existe pas
        if not folder_path.exists():
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                return False, f"Impossible de créer le répertoire :\n{e}"

        # Tester les droits d'écriture
        if not os.access(folder_path, os.W_OK):
            return False, f"Le répertoire {folder} n'est pas accessible en écriture."

        return True, ""
    
    def closeEvent(self, event: QCloseEvent) -> None:
        # En mode first-run, la croix doit fermer l'application
        if self._is_first_run:
            QApplication.instance().quit()
            event.accept()
        else:
            # En mode normal, se comporter comme Annuler
            # (restaurer le theme de l'apercu immediat).
            self.reject()
            event.accept()
    
    def quit_application(self):
        """En mode first-run, quitter l'application."""
        import sys
        sys.exit(0)

    def build_ui(self):
        #
        # Layout principal : onglets + actions.
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

        self.tabs = QTabWidget()

        self.tabs.addTab(
            self._construire_onglet_general(),
            "Général"
        )

        self.tabs.addTab(
            self._construire_onglet_llm(),
            "LLM (reformulation)"
        )

        layout.addWidget(
            self.tabs,
            stretch=1
        )

        #
        # ==================================================
        # Actions
        # ==================================================
        #
        layout.addSpacing(4)

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

        buttons_layout.setSpacing(8)

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

        # Apercu immediat : appliquer le theme des la
        # selection dans la liste deroulante, sans
        # attendre Enregistrer. Annuler (bouton ou
        # croix) restaure le theme enregistre.
        self.theme_combo.currentIndexChanged.connect(
            self.on_theme_selected
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

        #
        # Connexions LLM.
        #
        self.llm_fournisseur_combo.currentIndexChanged.connect(
            self.on_llm_fournisseur_change
        )

        self.llm_modele_combo.currentIndexChanged.connect(
            self.on_llm_modele_change
        )

        self.llm_tester_button.clicked.connect(
            self.tester_cle_llm
        )

        self.llm_catalogue_button.clicked.connect(
            self.ouvrir_editeur_catalogue
        )

    def _construire_onglet_general(self) -> QWidget:
        """
        Onglet Général : clé ElevenLabs, répertoire
        des projets, thème.
        """

        onglet = QWidget()

        layout = QVBoxLayout(onglet)

        layout.setContentsMargins(0, 10, 0, 10)

        layout.setSpacing(12)

        # Message d'introduction en mode first-run
        if self._is_first_run:
            intro_label = QLabel(
                "<b>Configuration initiale requise</b><br><br>"
                "Veuillez configurer le répertoire où vos réunions seront enregistrées.<br>"
                "La clé API ElevenLabs est facultative et peut être ajoutée ultérieurement.<br><br>"
                "<i>Cette configuration ne peut pas être ignorée.</i>"
            )
            intro_label.setWordWrap(True)
            intro_label.setStyleSheet("color: #555;")
            layout.addWidget(intro_label)
            layout.addSpacing(10)
        
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

        api_layout.setSpacing(8)

        self.api_key_edit = QLineEdit()

        self.api_key_edit.setText(
            self._credential_store.get_api_key()
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
                "Répertoire des réunions <span style='color: #D32F2F;'>*</span>"
            )
        else:
            projects_label = QLabel(
                "Répertoire des réunions"
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

        projects_layout.setSpacing(8)

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

        theme_layout.setSpacing(8)

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

        theme_layout.addWidget(theme_label)

        theme_layout.addStretch()

        theme_layout.addWidget(self.theme_combo)

        layout.addLayout(theme_layout)

        layout.addStretch()

        return onglet

    def _construire_onglet_llm(self) -> QWidget:
        """
        Onglet LLM (P15.2) : fournisseur du
        catalogue, clé masquée avec « Tester la clé »,
        modèle et réglages adaptés aux capacités
        déclarées (l'UI n'affiche jamais un réglage
        non déclaré — règle d'invariance 2).
        """

        onglet = QWidget()

        layout = QVBoxLayout(onglet)

        layout.setContentsMargins(0, 10, 0, 10)

        layout.setSpacing(8)

        formulaire = QFormLayout()
        formulaire.setSpacing(8)

        #
        # Fournisseur.
        #
        self.llm_fournisseur_combo = QComboBox()

        formulaire.addRow(
            "Fournisseur",
            self.llm_fournisseur_combo
        )

        #
        # Clé API du fournisseur (masquée, une par
        # fournisseur, jamais en clair ailleurs que
        # dans le CredentialStore).
        #
        cle_layout = QHBoxLayout()
        cle_layout.setContentsMargins(0, 0, 0, 0)
        cle_layout.setSpacing(8)

        self.llm_cle_edit = QLineEdit()
        self.llm_cle_edit.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        self.llm_tester_button = QPushButton(
            "Tester la clé"
        )
        self.llm_tester_button.setFixedWidth(110)

        cle_layout.addWidget(
            self.llm_cle_edit,
            1
        )

        cle_layout.addWidget(self.llm_tester_button)

        formulaire.addRow(
            "Clé API",
            cle_layout
        )

        self.llm_test_statut = QLabel("Non testée.")

        self.llm_test_statut.setStyleSheet(
            "font-size: 12px; color: #666666;"
        )

        self.llm_test_statut.setWordWrap(True)

        formulaire.addRow(
            "",
            self.llm_test_statut
        )

        #
        # Modèle du fournisseur.
        #
        self.llm_modele_combo = QComboBox()

        formulaire.addRow(
            "Modèle",
            self.llm_modele_combo
        )

        #
        # Température : affichée uniquement si le
        # modèle la déclare (capacités).
        #
        self.llm_temperature_spin = QDoubleSpinBox()
        self.llm_temperature_spin.setRange(0.0, 2.0)
        self.llm_temperature_spin.setSingleStep(0.1)
        self.llm_temperature_spin.setDecimals(2)

        self.llm_temperature_ligne = QWidget()
        ligne_layout = QHBoxLayout(self.llm_temperature_ligne)
        ligne_layout.setContentsMargins(0, 0, 0, 0)
        ligne_layout.addWidget(self.llm_temperature_spin)
        ligne_layout.addStretch()

        formulaire.addRow(
            "Température",
            self.llm_temperature_ligne
        )

        #
        # max_tokens : plafonné au contexte du
        # modèle déclaré.
        #
        self.llm_max_tokens_spin = QSpinBox()
        self.llm_max_tokens_spin.setRange(0, 1_000_000)
        self.llm_max_tokens_spin.setSingleStep(256)
        self.llm_max_tokens_spin.setSpecialValueText(
            "Automatique"
        )

        self.llm_max_tokens_ligne = QWidget()
        ligne_layout = QHBoxLayout(self.llm_max_tokens_ligne)
        ligne_layout.setContentsMargins(0, 0, 0, 0)
        ligne_layout.addWidget(self.llm_max_tokens_spin)
        ligne_layout.addStretch()

        formulaire.addRow(
            "Tokens max par réponse",
            self.llm_max_tokens_ligne
        )

        #
        # Effort de raisonnement : affiché
        # uniquement si le modèle le déclare.
        #
        self.llm_effort_combo = QComboBox()
        self.llm_effort_combo.addItem("Faible", "low")
        self.llm_effort_combo.addItem("Moyen", "medium")
        self.llm_effort_combo.addItem("Élevé", "high")

        self.llm_effort_ligne = QWidget()
        ligne_layout = QHBoxLayout(self.llm_effort_ligne)
        ligne_layout.setContentsMargins(0, 0, 0, 0)
        ligne_layout.addWidget(self.llm_effort_combo)
        ligne_layout.addStretch()

        formulaire.addRow(
            "Effort de raisonnement",
            self.llm_effort_ligne
        )

        layout.addLayout(formulaire)

        #
        # Catalogue.
        #
        self.llm_catalogue_button = QPushButton(
            "Modifier le catalogue..."
        )

        self.llm_catalogue_button.setToolTip(
            "Ajouter un fournisseur (Ollama, LM Studio, "
            "OpenRouter...), un modèle, ou mettre les "
            "prix à jour"
        )

        catalogue_layout = QHBoxLayout()
        catalogue_layout.addStretch()
        catalogue_layout.addWidget(self.llm_catalogue_button)

        layout.addLayout(catalogue_layout)

        layout.addStretch()

        #
        # Tous les champs existent : chargement
        # initial (fournisseurs, modèles, clé,
        # capacités).
        #
        self._remplir_fournisseurs()

        return onglet

    #
    # ==================================================
    # LLM : catalogue, fournisseur, modèle
    # ==================================================
    #

    def _charger_catalogue_llm(self):

        try:
            self._catalogue_llm = charger_catalogue()

        except CatalogueError:

            #
            # Catalogue utilisateur illisible : repli
            # sur l'embarqué, sans l'écraser (il sera
            # revalidé à l'enregistrement).
            #
            self._catalogue_llm = catalogue_par_defaut()

    def _remplir_fournisseurs(self):
        """
        Remplit la liste des fournisseurs du
        catalogue et sélectionne celui mémorisé
        (à défaut, le premier).
        """

        self.llm_fournisseur_combo.blockSignals(True)
        self.llm_fournisseur_combo.clear()

        for fournisseur in (
            self._catalogue_llm.fournisseurs
        ):
            self.llm_fournisseur_combo.addItem(
                fournisseur.nom,
                fournisseur.id
            )

        self.llm_fournisseur_combo.blockSignals(False)

        config = self.settings.get_llm_config()

        index = self.llm_fournisseur_combo.findData(
            config.get("fournisseur")
        )

        if index < 0:
            index = 0

        self.llm_fournisseur_combo.setCurrentIndex(index)

        # Déclenche le chargement initial (modèles,
        # clé, capacités).
        self.on_llm_fournisseur_change()

    def _fournisseur_courant(self):

        fournisseur_id = (
            self.llm_fournisseur_combo.currentData()
        )

        if fournisseur_id is None:
            return None

        return (
            self._catalogue_llm.chercher_fournisseur(
                fournisseur_id
            )
        )

    def on_llm_fournisseur_change(self, *args):
        """
        Changement de fournisseur : mémoriser la clé
        saisie du fournisseur précédent (elle ne se
        perd pas), charger la clé du fournisseur
        courant, ses modèles et ses réglages.
        """

        #
        # Persister la clé saisie du fournisseur
        # précédent dans le CredentialStore.
        #
        if (
            self._ancien_fournisseur_id is not None
            and hasattr(self, "llm_cle_edit")
        ):
            self._credential_store.set_cle_llm(
                self._ancien_fournisseur_id,
                self.llm_cle_edit.text().strip()
            )

        fournisseur = self._fournisseur_courant()

        self._ancien_fournisseur_id = (
            fournisseur.id if fournisseur else None
        )

        if fournisseur is None:

            self.llm_cle_edit.setText("")
            self.llm_test_statut.setText("Non testée.")

            self.llm_modele_combo.blockSignals(True)
            self.llm_modele_combo.clear()
            self.llm_modele_combo.blockSignals(False)

            return

        #
        # Clé du fournisseur courant (fournisseur
        # local : champ vide, aucune clé requise).
        #
        self.llm_cle_edit.setText(
            self._credential_store.get_cle_llm(
                fournisseur.id
            )
        )

        if not fournisseur.necessite_cle:
            self.llm_test_statut.setStyleSheet(
                "font-size: 12px; color: #666666;"
            )
            self.llm_test_statut.setText(
                "Fournisseur local : aucune clé requise."
            )
        else:
            self.llm_test_statut.setStyleSheet(
                "font-size: 12px; color: #666666;"
            )
            self.llm_test_statut.setText("Non testée.")

        #
        # P16-bis (retour relecture §17) : résultat
        # du test mémorisé pour CE fournisseur —
        # revenir dessus ne repart pas de « Non
        # testée. ».
        #
        statut = self._statuts_test.get(
            fournisseur.id
        )

        if statut is not None:
            self.llm_test_statut.setStyleSheet(
                f"font-size: 12px; "
                f"color: {statut[1]};"
            )
            self.llm_test_statut.setText(statut[0])

        self._remplir_modeles()

    def _remplir_modeles(self):
        """
        Modèles du fournisseur courant ; sélectionne
        celui mémorisé (à défaut, le premier).
        """

        fournisseur = self._fournisseur_courant()

        self.llm_modele_combo.blockSignals(True)
        self.llm_modele_combo.clear()

        if fournisseur is not None:

            for modele in fournisseur.modeles:
                self.llm_modele_combo.addItem(
                    modele.nom_affiche,
                    modele.id
                )

        self.llm_modele_combo.blockSignals(False)

        if (
            fournisseur is None
            or not fournisseur.modeles
        ):
            return

        config = self.settings.get_llm_config()

        index = self.llm_modele_combo.findData(
            config.get("modele")
        )

        if index < 0:
            index = 0

        self.llm_modele_combo.setCurrentIndex(index)

        # Applique les capacités du modèle courant.
        self.on_llm_modele_change()

    def _modele_courant(self):

        fournisseur = self._fournisseur_courant()

        if fournisseur is None:
            return None

        modele_id = self.llm_modele_combo.currentData()

        if modele_id is None:
            return None

        return fournisseur.chercher_modele(modele_id)

    def on_llm_modele_change(self, *args):
        """
        Règle d'invariance 2 : n'afficher que les
        réglages déclarés dans les capacités du
        modèle courant, max_tokens plafonné au
        contexte déclaré.
        """

        modele = self._modele_courant()

        config = self.settings.get_llm_config()

        if modele is None:

            self.llm_temperature_ligne.setVisible(False)
            self.llm_effort_ligne.setVisible(False)

            self.llm_max_tokens_spin.setRange(
                0,
                1_000_000
            )

            self.llm_max_tokens_spin.setValue(0)

            return

        reglages = reglages_affichables(modele)

        #
        # Température : uniquement si supportée.
        #
        temperature_visible = (
            "temperature" in reglages
        )

        self.llm_temperature_ligne.setVisible(
            temperature_visible
        )

        if temperature_visible:

            self.llm_temperature_spin.setValue(
                float(config.get("temperature") or 0.3)
            )

        #
        # Effort de raisonnement : uniquement si
        # déclaré.
        #
        self.llm_effort_ligne.setVisible(
            "effort_raisonnement" in reglages
        )

        #
        # max_tokens : plafond au contexte du modèle.
        #
        maximum = reglages["max_tokens"]["maximum"]

        if maximum is None:
            maximum = 1_000_000

        self.llm_max_tokens_spin.setRange(
            0,
            maximum
        )

        self.llm_max_tokens_spin.setValue(
            int(config.get("max_tokens") or 0)
        )

    def tester_cle_llm(self):
        """
        « Tester la clé » : appel léger de validation
        (liste des modèles) ; état valide / invalide,
        sans jamais afficher la clé.
        """

        fournisseur = self._fournisseur_courant()

        if fournisseur is None:
            return

        cle = self.llm_cle_edit.text().strip()

        try:

            client = creer_client(
                fournisseur,
                cle
            )

            resultat = client.tester_connexion()

        except ErreurLLM as e:

            self.llm_test_statut.setStyleSheet(
                "font-size: 12px; color: #D32F2F;"
            )

            #
            # Seule une erreur d'authentification condamne
            # la clé ; une erreur réseau, serveur (5xx) ou
            # quota est transitoire : la clé n'est pas en
            # cause et le test peut être relancé.
            #
            if e.type == "cle_invalide":
                texte = f"Clé invalide : {e.message}"
            elif e.type in ("reseau", "timeout"):
                texte = (
                    "Test impossible pour le moment "
                    f"(erreur réseau ou serveur) : {e.message}"
                )
            elif e.type == "quota":
                texte = f"Limite d'appels atteinte : {e.message}"
            else:
                texte = f"Échec du test : {e.message}"

            self._enregistrer_statut_test(
                texte,
                "#D32F2F"
            )

            return

        if not fournisseur.necessite_cle and not cle:
            texte = (
                f"Connexion validée ({resultat['message']})"
            )
        else:
            texte = (
                f"Clé valide. {resultat['message']}"
            )

        self._enregistrer_statut_test(
            texte,
            "#2E7D32"
        )

    def _enregistrer_statut_test(
        self,
        texte: str,
        couleur: str
    ):
        """
        Affiche le résultat du test de la clé du
        fournisseur courant et le mémorise par
        fournisseur (retour relecture §17) :
        changer de fournisseur et revenir conserve
        le résultat.
        """

        fournisseur = self._fournisseur_courant()

        if fournisseur is not None:
            self._statuts_test[fournisseur.id] = (
                (texte, couleur)
            )

        self.llm_test_statut.setStyleSheet(
            f"font-size: 12px; color: {couleur};"
        )

        self.llm_test_statut.setText(texte)

    def ouvrir_editeur_catalogue(self):
        """
        Ouvre l'éditeur du catalogue ; à la
        sauvegarde, recharge fournisseurs et modèles.
        """

        dialogue = CatalogueLLMDialog(
            parent=self,
            catalogue=self._catalogue_llm
        )

        if dialogue.exec() != QDialog.DialogCode.Accepted:
            return

        self._charger_catalogue_llm()

        self._remplir_fournisseurs()

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
        self._credential_store.set_api_key(
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

        #
        # Paramétrage LLM (P15) : sélection
        # mémorisée + clé par fournisseur dans le
        # CredentialStore (jamais dans les
        # réglages en clair).
        #
        fournisseur = self._fournisseur_courant()

        if fournisseur is not None:

            self._credential_store.set_cle_llm(
                fournisseur.id,
                self.llm_cle_edit.text().strip()
            )

        config = self.settings.get_llm_config()

        config["fournisseur"] = (
            self.llm_fournisseur_combo.currentData()
        )

        config["modele"] = (
            self.llm_modele_combo.currentData()
        )

        if self.llm_temperature_ligne.isVisible():
            config["temperature"] = (
                self.llm_temperature_spin.value()
            )

        config["max_tokens"] = (
            self.llm_max_tokens_spin.value() or None
        )

        if self.llm_effort_ligne.isVisible():
            config["effort_raisonnement"] = (
                self.llm_effort_combo.currentData()
            )

        self.settings.set_llm_config(config)

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

    def on_theme_selected(self):
        """
        Apercu immediat du theme choisi dans la
        liste deroulante.
        """
        theme = (
            self.theme_combo.currentData()
        )

        app = QApplication.instance()

        if app is None:
            return

        ThemeManager.apply_theme(
            app,
            theme
        )

    def restore_saved_theme(self):
        """
        Reapplique le theme enregistre : appele a
        l'annulation, l'apercu immediat ayant pu
        changer le theme affiche.
        """
        app = QApplication.instance()

        if app is None:
            return

        ThemeManager.apply_theme(
            app,
            self.settings.get_theme()
        )

    def reject(self):
        # Annulation : restaurer le theme enregistre
        # si l'apercu immediat l'a change.
        self.restore_saved_theme()
        super().reject()

    def test_connection(self):

        self._credential_store.set_api_key(
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
            "Choisir le répertoire des réunions",
            default_dir
        )

        if folder:

            self.projects_root_edit.setText(
                folder
            )
