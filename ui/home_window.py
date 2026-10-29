from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
    QMenu,
    QInputDialog,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import (
    QThread,
    Qt,
    QSize,
    QUrl,
)
from PySide6.QtGui import (
    QPixmap,
    QFont,
    QFontDatabase,
    QIcon,
    QPalette,
    QColor,
    QDesktopServices,
)

from pathlib import Path

from services.settings import SettingsManager
from services.api_capabilities import can_access_account_info, has_transcription_api
from ui.new_transcription_dialog import NewTranscriptionDialog
from ui.settings_dialog import SettingsDialog
from ui.elevenlabs_account_dialog import ElevenLabsAccountDialog
from ui.progress_dialog import ProgressDialog
from ui.main_window import MainWindow
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
from services.etude_io import (
    EtudeError,
    creer_etude,
    ouvrir_etude,
)
from services.etude_schema import EtudeFormatError
from ui.etude_window import EtudeWindow
from ui.stepper import StepperBar

class HomeWindow(QWidget):

    def __init__(self, settings=None):
        super().__init__()

        #
        # Réglages injectables (fenêtre à pile unique,
        # P16-bis §11 : les tests isolent la
        # configuration réelle de l'utilisateur).
        #
        self.settings = (
            settings
            if settings is not None
            else SettingsManager()
        )
        self.transcription_thread = None
        self.transcription_worker = None
        self.progress_dialog = None
        self.transcription_started = False

        self.setWindowTitle(
            "Transcript Studio"
        )

        self.resize(
            550,
            500
        )

        self.build_ui()

    def build_ui(self):
        """
        Hub d'accueil (P18.6a, spec navigation §2) :
        bandeau app (uniquement ici, invariant §9.2),
        salutation « Bonjour », trois tuiles, dernières
        réunions en une colonne de mini-tuiles (stepper
        complet ①→⑥ conservé — réunions autonomes),
        études récentes.
        """

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(10)

        #
        # Bandeau app — n'apparaît QUE sur l'accueil
        # (spec §1.2, invariant §9.2) : logo, sous-titre,
        # version, pastilles de services, ⚙, ?.
        #
        self.bandeau = QWidget()
        self.bandeau.setObjectName("bandeau_app")

        header_layout = QHBoxLayout(self.bandeau)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(14)

        icon_label = QLabel()
        pixmap = QPixmap(str(resource_path("icons/logo.png")))
        icon_label.setPixmap(
            pixmap.scaled(
                96,
                96,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        self.title_label = QLabel("Transcript Studio")

        # Police systeme : Segoe UI Light n'existe que
        # sous Windows.
        title_font = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.GeneralFont
        )
        title_font.setPointSize(26)
        title_font.setWeight(QFont.Weight.Light)
        self.title_label.setFont(title_font)

        self.subtitle_label = QLabel(
            "Prétraitement audio et transcription assistée par ElevenLabs"
        )
        self.version_label = QLabel("Version 1.0 — Octobre 2026")

        #
        # Pastilles de services (spec §2.2) : verte si
        # clé configurée, grise sinon, info-bulle au
        # survol. FFmpeg et Bible n'y figurent pas
        # (diagnostic uniquement pour FFmpeg ; la version
        # de Bible est propre à chaque étude).
        #
        self.api_pastille = QLabel("● Transcription ElevenLabs")
        self.llm_pastille = QLabel("● Service IA")

        for pastille in (
            self.api_pastille,
            self.llm_pastille,
        ):
            pastille.setStyleSheet(
                "font-size: 12px;"
            )

        #
        # Libellés d'état complets conservés (masqués :
        # le hub affiche des pastilles) — ils portent le
        # détail « configuré / non configuré » des tests
        # P16-bis et servent d'info-bulles.
        #
        self.api_status_label = QLabel("")
        self.api_status_label.setStyleSheet("font-size: 12px; color: #666666;")
        self.api_status_label.setVisible(False)

        self.llm_status_label = QLabel("")
        self.llm_status_label.setStyleSheet("font-size: 12px; color: #666666;")
        self.llm_status_label.setVisible(False)

        pastilles_layout = QHBoxLayout()
        pastilles_layout.setContentsMargins(0, 0, 0, 0)
        pastilles_layout.setSpacing(16)
        pastilles_layout.addWidget(self.api_pastille)
        pastilles_layout.addWidget(self.llm_pastille)
        pastilles_layout.addStretch()

        title_layout.addWidget(self.title_label)
        title_layout.addSpacing(4)
        title_layout.addWidget(self.subtitle_label)
        title_layout.addSpacing(8)
        title_layout.addWidget(self.version_label)
        title_layout.addSpacing(6)
        title_layout.addLayout(pastilles_layout)

        header_layout.addWidget(
            icon_label,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        #
        # Boutons du bandeau : ⚙ Paramètres et ? Aide.
        #
        self.settings_button = QPushButton("⚙ Paramètres")
        self.settings_button.setIcon(
            QIcon(str(resource_path("icons/settings.svg")))
        )
        self.settings_button.setToolTip("Configurer Transcript Studio")

        self.help_button = QPushButton("? Aide")
        self.help_button.setIcon(
            QIcon(str(resource_path("icons/info-square-rounded.svg")))
        )
        self.help_button.setToolTip("Ouvrir le manuel utilisateur")

        for button in (
            self.settings_button,
            self.help_button,
        ):
            button.setFixedSize(140, 34)
            button.setIconSize(QSize(18, 18))

        header_layout.addWidget(self.settings_button)
        header_layout.addWidget(self.help_button)

        layout.addWidget(self.bandeau)

        #
        # Salutation (spec §2.3) : « Bonjour », sans
        # prénom.
        #
        self.salutation_label = QLabel("Bonjour")
        self.salutation_label.setStyleSheet(
            "font-size: 18px; font-weight: 600;"
        )
        layout.addWidget(self.salutation_label)

        #
        # Trois tuiles (libellés exacts, spec §2.1).
        #
        tuiles_layout = QHBoxLayout()
        tuiles_layout.setContentsMargins(0, 0, 0, 0)
        tuiles_layout.setSpacing(12)

        self.tuile_nouvelle = QPushButton(
            "Nouvelle transcription"
        )
        self.tuile_reprendre = QPushButton(
            "Reprendre une réunion"
        )
        self.tuile_etudes = QPushButton("Études")

        self.tuile_nouvelle.setIcon(
            QIcon(str(resource_path("icons/bubble-text.svg")))
        )
        self.tuile_reprendre.setIcon(
            QIcon(str(resource_path("icons/folder-open.svg")))
        )

        self.tuile_nouvelle.setToolTip(
            "Créer une nouvelle réunion "
            "(enregistrement transcrit)"
        )
        self.tuile_reprendre.setToolTip(
            "Ouvrir une réunion existante sur le disque"
        )
        self.tuile_etudes.setToolTip(
            "Une étude est un regroupement de réunions "
            "ayant pour objet un thème spécifique"
        )

        for tuile in (
            self.tuile_nouvelle,
            self.tuile_reprendre,
            self.tuile_etudes,
        ):
            tuile.setObjectName("tuile_hub")
            tuile.setMinimumSize(220, 84)
            tuile.setIconSize(QSize(24, 24))
            tuiles_layout.addWidget(tuile)

        tuiles_layout.addStretch()

        layout.addLayout(tuiles_layout)
        layout.addSpacing(6)

        #
        # Dernières réunions (spec §2.4) : liste en une
        # colonne de mini-tuiles — titre, étude (ou
        # « Réunion autonome » + lien « rattacher à une
        # étude… »), stepper complet ①→⑥, coût.
        #
        layout.addWidget(QLabel("Dernières réunions"))

        self.dernieres_scroll = QScrollArea()
        self.dernieres_scroll.setWidgetResizable(True)
        self.dernieres_scroll.setFrameShape(
            QScrollArea.Shape.NoFrame
        )

        self.dernieres_conteneur = QWidget()
        self.dernieres_layout = QVBoxLayout(
            self.dernieres_conteneur
        )
        self.dernieres_layout.setContentsMargins(0, 0, 0, 0)
        self.dernieres_layout.setSpacing(6)
        self.dernieres_layout.addStretch()

        self.dernieres_scroll.setWidget(
            self.dernieres_conteneur
        )

        layout.addWidget(
            self.dernieres_scroll,
            stretch=1,
        )

        #
        # Études récentes (tuile « Études »).
        #
        layout.addWidget(QLabel("Études"))

        self.recent_etudes = QListWidget()
        self.recent_etudes.setMinimumHeight(80)

        for etude_folder in self.settings.cleanup_recent_etudes():
            dossier = Path(etude_folder)
            item = QListWidgetItem(dossier.name)
            item.setData(
                Qt.ItemDataRole.UserRole,
                str(dossier),
            )
            item.setToolTip(str(dossier))
            self.recent_etudes.addItem(item)

        self.recent_etudes.setToolTip(
            "Études récentes — double-clic pour ouvrir"
        )

        self.recent_etudes.itemDoubleClicked.connect(
            self.ouvrir_etude_recente
        )

        layout.addWidget(
            self.recent_etudes,
        )
        layout.addSpacing(6)

        etudes_actions_layout = QHBoxLayout()
        etudes_actions_layout.setContentsMargins(0, 0, 0, 0)
        etudes_actions_layout.setSpacing(10)

        self.new_etude_button = QPushButton("Nouvelle étude")
        self.open_etude_button = QPushButton(
            "Ouvrir depuis un dossier…"
        )

        self.ouvrir_etude_selection_button = QPushButton(
            "Ouvrir l'étude sélectionnée"
        )
        self.ouvrir_etude_selection_button.setToolTip(
            "Ouvrir l'étude sélectionnée dans la liste "
            "ci-dessus : réunions, reformulation "
            "littéraire, résumé, synthèse"
        )
        self.ouvrir_etude_selection_button.clicked.connect(
            self.ouvrir_etude_selection
        )

        self.new_etude_button.setToolTip(
            "Créer une étude regroupant des réunions"
        )
        self.open_etude_button.setToolTip(
            "Choisir un dossier étude sur le disque "
            "(il doit contenir un etude.json)"
        )

        self.new_etude_button.clicked.connect(
            self.creer_etude_ui
        )
        self.open_etude_button.clicked.connect(
            self.ouvrir_etude_dialogue
        )

        etudes_actions_layout.addWidget(self.new_etude_button)
        etudes_actions_layout.addWidget(self.open_etude_button)
        etudes_actions_layout.addWidget(
            self.ouvrir_etude_selection_button
        )
        etudes_actions_layout.addStretch()
        layout.addLayout(etudes_actions_layout)

        #
        # Connexions des tuiles.
        #
        self.tuile_nouvelle.clicked.connect(
            self.new_transcription
        )
        self.tuile_reprendre.clicked.connect(
            self.open_project
        )
        self.tuile_etudes.clicked.connect(
            self.focus_etudes
        )
        self.settings_button.clicked.connect(
            self.open_settings
        )
        self.help_button.clicked.connect(open_user_manual)

        # Couleurs du bandeau (recalculees apres un
        # changement de theme) et pastilles.
        self.update_header_colors()
        self.update_api_status()
        self.maj_statut_llm()

        # Dernieres reunions.
        self.refresh_dernieres_reunions()

    def focus_etudes(self):
        """
        Tuile « Études » : met le focus sur la section
        Études du hub.
        """

        self.recent_etudes.setFocus()
        self.recent_etudes.setCurrentRow(0)

    # ==================================================
    # Dernières réunions (mini-tuiles du hub, P18.6a).
    # ==================================================

    def refresh_dernieres_reunions(self):
        """
        Reconstruit les mini-tuiles des dernières
        réunions (une colonne) : titre, étude ou
        « Réunion autonome » + lien de rattachement,
        stepper ①→⑥, coût.
        """

        while self.dernieres_layout.count() > 1:

            item = self.dernieres_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        projets = self.settings.cleanup_recent_projects()
        etudes = self.settings.cleanup_recent_etudes()

        if not projets:

            vide = QLabel(
                "Aucune réunion pour l'instant — "
                "commencez par « Nouvelle transcription »."
            )
            vide.setStyleSheet(
                "color: #8A8A8A; font-style: italic;"
            )

            self.dernieres_layout.insertWidget(
                0,
                vide
            )

            return

        for chemin in projets:

            tuile = self._construire_mini_tuile(
                chemin,
                etudes
            )

            if tuile is None:
                continue

            self.dernieres_layout.insertWidget(
                self.dernieres_layout.count() - 1,
                tuile
            )

    def _construire_mini_tuile(
        self,
        chemin,
        etudes
    ):
        """
        Une mini-tuile de réunion : titre, badge d'étude
        (ou « Réunion autonome » + lien « rattacher à une
        étude… »), stepper ①→⑥ compact, coût, ouverture.

        Retourne None si le projet est illisible (la
        liste des récents est déjà nettoyée par les
        réglages pour les fichiers disparus).
        """

        chemin = Path(chemin)

        try:
            projet = load_project(str(chemin))
        except Exception:
            return None

        from services.avancement import (
            cout_reunion,
            etapes_reunion,
        )
        from services.rattachement import (
            rattachement_de,
        )

        rattachement = rattachement_de(
            chemin,
            etudes
        )

        etude_ouverte = None
        nom_reunion = None
        titre_etude = None
        cout = 0.0

        if rattachement is not None:

            dossier, nom_reunion = rattachement

            try:

                etude_ouverte = ouvrir_etude(dossier)

                titre_etude = (
                    etude_ouverte.etude.titre
                )

                cout = cout_reunion(
                    etude_ouverte,
                    nom_reunion
                )

            except Exception:
                etude_ouverte = None

        titre = (
            Path(chemin).parent.name
        )

        if (
            etude_ouverte is not None
            and nom_reunion in etude_ouverte.reunions
        ):

            titre = (
                etude_ouverte
                .reunions[nom_reunion]
                .titre_1
                or titre
            )

        etats = etapes_reunion(
            projet,
            etude_ouverte=etude_ouverte,
            nom=nom_reunion,
            settings=self.settings,
            chemin_projet=str(chemin)
        )

        cadre = QFrame()
        cadre.setObjectName("hub_mini_tuile")
        cadre.setStyleSheet(
            "QFrame#hub_mini_tuile {"
            "border: 1px solid #C8C8C8;"
            "border-radius: 6px;"
            "}"
        )
        cadre.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        cadre.customContextMenuRequested.connect(
            lambda pos, c=str(chemin): (
                self.afficher_menu_mini_tuile(cadre, c, pos)
            )
        )

        layout = QVBoxLayout(cadre)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(3)

        ligne_titre = QHBoxLayout()

        titre_label = QLabel(titre)
        titre_label.setStyleSheet(
            "font-weight: 600;"
        )
        titre_label.setToolTip(str(chemin))

        ligne_titre.addWidget(titre_label)
        ligne_titre.addStretch()

        cout_label = QLabel(
            f"Coût : {cout:.4f} $"
            if cout
            else "Coût : —"
        )
        cout_label.setStyleSheet(
            "color: #8A8A8A; font-size: 11px;"
        )
        ligne_titre.addWidget(cout_label)

        layout.addLayout(ligne_titre)

        ligne_etude = QHBoxLayout()

        if titre_etude:

            badge = QLabel(f"Étude « {titre_etude} »")
            badge.setStyleSheet(
                "color: #1565C0; font-size: 12px;"
            )
            ligne_etude.addWidget(badge)

        else:

            autonome = QLabel("Réunion autonome")
            autonome.setStyleSheet(
                "color: #8A8A8A; font-size: 12px;"
            )
            ligne_etude.addWidget(autonome)

            rattacher_link = QPushButton(
                "rattacher à une étude…"
            )
            rattacher_link.setFlat(True)
            rattacher_link.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            rattacher_link.setStyleSheet(
                "color: #1565C0;"
                "text-decoration: underline;"
                "border: none;"
                "font-size: 12px;"
                "padding: 0;"
            )
            rattacher_link.clicked.connect(
                lambda checked=False,
                c=str(chemin): (
                    self.rattacher_reunion(c)
                )
            )
            ligne_etude.addWidget(rattacher_link)

        ligne_etude.addStretch()

        layout.addLayout(ligne_etude)

        stepper = StepperBar(
            cliquable=False,
            compact=True
        )
        stepper.definir_etats(etats)

        layout.addWidget(stepper)

        ligne_actions = QHBoxLayout()

        ouvrir_button = QPushButton("Ouvrir")
        ouvrir_button.setFixedHeight(26)
        ouvrir_button.clicked.connect(
            lambda checked=False,
            c=str(chemin): (
                self.ouvrir_reunion_depuis_hub(c)
            )
        )

        ligne_actions.addWidget(ouvrir_button)
        ligne_actions.addStretch()

        layout.addLayout(ligne_actions)

        return cadre

    def ouvrir_reunion_depuis_hub(self, chemin):
        """
        Ouvre la page Réunion d'une mini-tuile (via la
        pile de navigation si la destination existe,
        sinon repli sur la page Correction — lancement
        autonome et tests).
        """

        if not Path(chemin).exists():
            QMessageBox.warning(
                self,
                "Réunion introuvable",
                (
                    "La réunion\n\n"
                    f"{chemin}\n\n"
                    "n'existe plus."
                )
            )
            return

        projet = load_project(str(chemin))

        navigation = getattr(self, "navigation", None)

        if (
            navigation is not None
            and hasattr(
                navigation,
                "ouvrir_reunion"
            )
        ):
            navigation.ouvrir_reunion(projet)
            return

        self.ouvrir_correction(projet)

    def rattacher_reunion(self, chemin):
        """
        « rattacher à une étude… » d'une mini-tuile
        autonome (spec §2.4) : disponible à tout
        moment, dès le prétraitement.
        """

        from ui.rattachement_dialog import (
            RattachementDialog
        )

        if not Path(chemin).exists():
            QMessageBox.warning(
                self,
                "Réunion introuvable",
                (
                    "La réunion\n\n"
                    f"{chemin}\n\n"
                    "n'existe plus."
                )
            )
            return

        dialogue = RattachementDialog(
            chemin,
            self.settings,
            parent=self
        )

        dialogue.exec()

        self.refresh_dernieres_reunions()

    def afficher_menu_mini_tuile(
        self,
        cadre,
        chemin,
        pos
    ):
        """
        Menu contextuel d'une mini-tuile : ouvrir la
        réunion, ouvrir son répertoire, la retirer de
        la liste (jamais du disque).
        """

        menu = QMenu(self)

        ouvrir_action = menu.addAction(
            "Ouvrir la réunion"
        )
        ouvrir_action.triggered.connect(
            lambda: self.ouvrir_reunion_depuis_hub(
                chemin
            )
        )

        dossier_action = menu.addAction(
            "Ouvrir le répertoire de la réunion"
        )
        dossier_action.triggered.connect(
            lambda: self._ouvrir_repertoire(chemin)
        )

        menu.addSeparator()

        retirer_action = menu.addAction(
            "Retirer de la liste des réunions récentes"
        )
        retirer_action.triggered.connect(
            lambda: self._retirer_recent(chemin)
        )

        menu.exec(
            cadre.mapToGlobal(pos)
        )

    def _ouvrir_repertoire(self, chemin):

        folder = Path(chemin).parent

        if not folder.is_dir():
            QMessageBox.warning(
                self,
                "Répertoire introuvable",
                (
                    "Le répertoire\n\n"
                    f"{folder}\n\n"
                    "n'existe plus."
                )
            )
            return

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(folder))
        )

    def _retirer_recent(self, chemin):

        self.settings.remove_recent_project(chemin)

        self.refresh_dernieres_reunions()

    def update_header_colors(self):
        theme = self.settings.get_theme()

        if theme == "dark":
            title_color = "#F0F0F0"
            subtitle_color = "#C0C0C0"
            version_color = "#A8A8A8"
        elif theme == "light":
            title_color = "#191919"
            subtitle_color = "#555555"
            version_color = "#777777"
        else:
            is_dark = (
                self.palette().window().color().lightness() < 128
            )
            if is_dark:
                title_color = "#F0F0F0"
                subtitle_color = "#C0C0C0"
                version_color = "#A8A8A8"
            else:
                title_color = "#191919"
                subtitle_color = "#555555"
                version_color = "#777777"

        self.title_label.setStyleSheet(
            f"color: {title_color}; font-size: 26px;"
        )
        self.subtitle_label.setStyleSheet(
            f"color: {subtitle_color}; font-size: 13px; font-weight: 400;"
        )
        self.version_label.setStyleSheet(
            f"color: {version_color}; font-size: 12px;"
        )


    def open_settings(self):
        dialog = SettingsDialog(self)
        result = dialog.exec()

        if result:
            self.settings.load()
            self.update_header_colors()
            self.update_api_status()
            self.maj_statut_llm()
                
    def update_api_status(self):
        """
        Pastille « Transcription ElevenLabs » (spec §2.2)
        : verte si la clé API est configurée, grise
        sinon, détail dans l'info-bulle.
        """
        if has_transcription_api():
            self.api_status_label.setText(
                "Service de transcription : configuré"
            )
            self.api_pastille.setStyleSheet(
                "font-size: 12px; color: #2E7D32;"
            )
        else:
            self.api_status_label.setText(
                "Service de transcription : non configuré"
            )
            self.api_pastille.setStyleSheet(
                "font-size: 12px; color: #8A8A8A;"
            )

        self.api_pastille.setToolTip(
            self.api_status_label.text()
        )

    def maj_statut_llm(self):
        """
        Pastille « Service IA » (spec §2.2) : verte si au
        moins un fournisseur du catalogue a sa clé
        enregistrée (ou fournisseur local sans clé),
        grise sinon. Détail (noms des fournisseurs)
        dans l'info-bulle — retour relecture P16-bis.
        """

        from services.credential_store import CredentialStore
        from services.llm.catalogue import (
            charger_catalogue,
        )

        try:
            catalogue = charger_catalogue()
        except Exception:
            catalogue = None

        noms = []

        if catalogue is not None:

            store = CredentialStore(
                self.settings.app_folder / "settings.json"
            )

            for fournisseur in catalogue.fournisseurs:

                if (
                    not fournisseur.necessite_cle
                    or store.has_cle_llm(fournisseur.id)
                ):
                    noms.append(fournisseur.nom)

        if noms:
            self.llm_status_label.setText(
                "Service de reformulation : configuré — "
                + ", ".join(noms)
            )
            self.llm_pastille.setStyleSheet(
                "font-size: 12px; color: #2E7D32;"
            )
        else:
            self.llm_status_label.setText(
                "Service de reformulation : non configuré"
            )
            self.llm_pastille.setStyleSheet(
                "font-size: 12px; color: #8A8A8A;"
            )

        self.llm_pastille.setToolTip(
            self.llm_status_label.text()
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
                # Vérifier si l'utilisateur a demandé à ouvrir les paramètres
                if dialog.should_open_settings():
                    self.open_settings()
                
                try:
                    manager.delete_provisional_project(
                        project_folder
                    )

                except OSError as e:
                    QMessageBox.critical(
                        self,
                        "Erreur de nettoyage",
                        (
                            "Impossible de supprimer "
                            "la réunion provisoire.\n\n"
                            + str(e)
                        )
                    )

                return

            options = dialog.get_options()

            self.start_transcription(
                project_audio_file,
                options
            )

            return
            
            
        if mode == (
            TranscriptionEntryDialog.MODE_PREPROCESSING
        ):
            self.start_audio_loading(
                project_audio_file,
                project_folder
            )

            return     

    def refresh_recent_projects(self):
        """
        Les réunions récentes vivent désormais dans les
        mini-tuiles du hub (P18.6a).
        """

        self.refresh_dernieres_reunions()

    def open_project(self):
        """
        Tuile « Reprendre une réunion » : choix d'un
        fichier .sttproj sur le disque, ouverture de
        la page Réunion.
        """

        projects_root = (
            self.settings
            .get_projects_root()
        )

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir une réunion",
            projects_root,
            "Réunion (*.sttproj)"
        )

        if not filename:
            return

        self.ouvrir_reunion_depuis_hub(filename)
    #
    # Navigation (P16-bis §11 : pile unique).
    #

    def ouvrir_correction(self, projet):
        """
        Ouvre la page Réunion « Correction de
        transcription » (éditeur v1) : via la pile de
        la fenêtre principale si présente, sinon en
        fenêtre autonome (lancement direct/tests).
        """

        navigation = getattr(self, "navigation", None)

        if navigation is not None:
            navigation.ouvrir_correction(projet)
            return

        self.editor = MainWindow(
            project
        )

        self.editor.show()

        self.close()

    #
    # Etudes (v2 - P14.3)
    #

    def creer_etude_ui(self):
        """
        Crée une étude : choix du dossier, titre,
        structure complète du format étude.

        Dossier non vide autorisé avec confirmation
        explicite ; dossier déjà étude : refus dur
        avec ouverture proposée (ARBITRAGE_CREATION_ETUDE).
        """

        dossier = QFileDialog.getExistingDirectory(
            self,
            "Dossier de la nouvelle étude",
            self.settings.get_projects_root()
        )

        if not dossier:
            return

        dossier = Path(dossier)

        #
        # Dossier déjà étude : jamais d'écrasement —
        # proposer l'ouverture.
        #
        if (dossier / "etude.json").is_file():

            reponse = QMessageBox.question(
                self,
                "Dossier déjà étude",
                (
                    "Ce dossier est déjà une étude "
                    "(etude.json présent).\n\n"
                    "L'ouvrir plutôt ?\n\n"
                    "Pour créer une nouvelle étude, "
                    "saisissez plutôt un nom de nouveau "
                    "dossier pour la créer dedans."
                )
            )

            if reponse == QMessageBox.StandardButton.Yes:
                self.ouvrir_etude(dossier)

            return

        #
        # Dossier non vide : confirmation explicite
        # (l'étude s'ajoute à côté, rien d'existant
        # n'est modifié ni supprimé).
        #
        if dossier.exists():

            elements = len(list(dossier.iterdir()))

            if elements:

                reponse = QMessageBox.question(
                    self,
                    "Dossier non vide",
                    (
                        "Ce dossier contient déjà "
                        f"{elements} élément(s). "
                        "Créer l'étude ici quand même ?\n\n"
                        "Aucun fichier existant ne sera "
                        "modifié ni supprimé : l'étude "
                        "s'ajoute à côté (etude.json et "
                        "ses sous-dossiers)."
                    )
                )

                if reponse != QMessageBox.StandardButton.Yes:
                    return

        titre, ok = QInputDialog.getText(
            self,
            "Nouvelle étude",
            (
                "Titre de l'étude\n"
                "(un livre biblique par défaut, "
                "ou un thème libre) :"
            )
        )

        if not ok:
            return

        titre = titre.strip()

        if not titre:
            QMessageBox.warning(
                self,
                "Titre requis",
                "Une étude porte obligatoirement un titre."
            )
            return

        try:
            creer_etude(dossier, titre)
        except EtudeError as e:
            QMessageBox.warning(
                self,
                "Étude non créée",
                str(e)
            )
            return

        self.ouvrir_etude(dossier)

    def ouvrir_etude_dialogue(self):
        """
        « Ouvrir depuis un dossier… » (spec correctifs
        §12) : sélection d'un dossier, validation de
        la présence d'un etude.json (sinon message
        clair, rien ne s'ouvre), ouverture.
        """

        dossier = QFileDialog.getExistingDirectory(
            self,
            "Ouvrir une étude depuis un dossier",
            self.settings.get_projects_root()
        )

        if not dossier:
            return

        dossier = Path(dossier)

        if not (dossier / "etude.json").is_file():
            QMessageBox.warning(
                self,
                "Ce dossier n'est pas une étude",
                (
                    "Le dossier\n\n"
                    f"{dossier}\n\n"
                    "ne contient pas de etude.json : "
                    "ce n'est pas une étude.\n\n"
                    "Les études sont créées depuis "
                    "« Nouvelle étude »."
                )
            )
            return

        self.ouvrir_etude(dossier)

    def ouvrir_etude_recente(
        self,
        item
    ):
        """
        Ouvre l'étude double-cliquée dans la liste.
        """

        dossier = item.data(
            Qt.ItemDataRole.UserRole
        )

        if not dossier:
            return

        if not Path(dossier).is_dir():
            QMessageBox.warning(
                self,
                "Étude introuvable",
                (
                    "Le dossier\n\n"
                    f"{dossier}\n\n"
                    "n'existe plus."
                )
            )
            self.settings.remove_recent_etude(dossier)
            self.refresh_recent_etudes()
            return

        self.ouvrir_etude(dossier)

    def ouvrir_etude_selection(self):
        """
        Ouvre l'étude sélectionnée dans la liste des
        études récentes (bouton explicite, en plus
        du double-clic).
        """

        item = (
            self.recent_etudes.currentItem()
        )

        if item is None:
            QMessageBox.information(
                self,
                "Aucune étude sélectionnée",
                "Sélectionnez d'abord une étude dans "
                "la liste."
            )
            return

        self.ouvrir_etude_recente(item)

    def ouvrir_etude(self, dossier):
        """
        Ouvre la page Étude ; en cas de projet v1
        introuvable, la page s'affiche en mode
        dégradé sans bloquer. Navigation à pile
        unique : une étude déjà ouverte est réactivée.
        """

        navigation = getattr(self, "navigation", None)

        if navigation is not None:

            navigation.ouvrir_etude(dossier)

            self.refresh_recent_etudes()

            return

        try:
            self.etude_window = EtudeWindow(dossier)
        except EtudeFormatError:
            return

        self.etude_window.show()
        self.refresh_recent_etudes()

        self.close()

    def refresh_recent_etudes(self):
        """
        Recharge la liste des études récentes.
        """

        self.recent_etudes.clear()

        for etude_folder in self.settings.cleanup_recent_etudes():
            dossier = Path(etude_folder)
            item = QListWidgetItem(dossier.name)
            item.setData(
                Qt.ItemDataRole.UserRole,
                str(dossier),
            )
            item.setToolTip(str(dossier))
            self.recent_etudes.addItem(item)

    def transcription_finished(
        self,
        data
    ):
        if self.progress_dialog is not None:
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

        self.ouvrir_correction(project)

    def transcription_error(
        self,
        message
    ):
        if self.progress_dialog is not None:
            self.progress_dialog.close()

        QMessageBox.critical(
            self,
            "Erreur de transcription",
            message
        )

    def open_elevenlabs_account(self):

        if not can_access_account_info():
            QMessageBox.information(
                self,
                "Service non configuré",
                "Pour consulter les informations de votre compte ElevenLabs, "
                "vous devez d'abord configurer une clé API valide dans les paramètres."
            )
            return

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
            QMessageBox.critical(
                self,
                "Fichier audio indisponible",
                (
                    "Le fichier audio finalisé "
                    "est introuvable.\n\n"
                    "La transcription ne peut pas "
                    "être poursuivie."
                )
            )
            return

        processed_audio_file = Path(
            processed_audio_file
        )

        if not processed_audio_file.exists():
            QMessageBox.critical(
                self,
                "Fichier audio introuvable",
                (
                    "Le fichier audio finalisé "
                    "n'existe plus :\n\n"
                    f"{processed_audio_file}"
                )
            )
            return

        self.current_audio_file = (
            processed_audio_file
        )
        
        # Vérifier le mode de finalisation sélectionné
        finalize_mode = preprocess_dialog.get_finalize_mode()
        
        # Si l'utilisateur a choisi de finaliser uniquement, ne pas ouvrir NewTranscriptionDialog
        if finalize_mode == "finalize_only":
            # Finalisation sans transcription - projet validé, pas de transcription
            print(
                "[WORKFLOW] Audio finalisé uniquement :",
                processed_audio_file
            )
            return
        
        # Mode transcription : ouvrir NewTranscriptionDialog
        print(
            "[WORKFLOW] Audio transmis à NewTranscriptionDialog :",
            processed_audio_file
        )
        dialog = NewTranscriptionDialog(
            str(processed_audio_file),
            self
        )
        
        if not dialog.exec():
            # Vérifier si l'utilisateur a demandé à ouvrir les paramètres
            if dialog.should_open_settings():
                self.open_settings()
            
            try:
                manager = ProjectManager()

                manager.delete_provisional_project(
                    project_folder
                )

            except OSError as e:
                QMessageBox.critical(
                    self,
                    "Erreur de nettoyage",
                    (
                        "Impossible de supprimer "
                        "la réunion provisoire.\n\n"
                        + str(e)
                    )
                )

            return

        options = dialog.get_options()

        self.start_transcription(
            processed_audio_file,
            options
        )

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

    def start_transcription(
        self,
        audio_file,
        options
    ):
        if self.transcription_thread is not None:
            return

        audio_file = Path(
            audio_file
        )

        if not audio_file.exists():
            QMessageBox.critical(
                self,
                "Fichier audio introuvable",
                (
                    "Le fichier audio à transcrire "
                    "est introuvable.\n\n"
                    f"{audio_file}"
                )
            )
            return

        #
        # Dès cet instant, le projet ne doit
        # plus être considéré comme provisoire.
        #
        self.transcription_started = True

        self.current_audio_file = audio_file

        #
        # Fenêtre de progression existante.
        #
        self.progress_dialog = ProgressDialog(
            str(audio_file),
            self
        )

        self.progress_dialog.setWindowModality(
            Qt.WindowModal
        )

        #
        # Thread.
        #
        self.transcription_thread = QThread(
            self
        )

        self.transcription_worker = (
            TranscriptionWorker(
                str(audio_file),
                options
            )
        )

        self.transcription_worker.moveToThread(
            self.transcription_thread
        )

        #
        # Démarrage.
        #
        self.transcription_thread.started.connect(
            self.transcription_worker.run
        )

        #
        # Succès.
        #
        self.transcription_worker.finished.connect(
            self.transcription_finished
        )

        self.transcription_worker.finished.connect(
            self.transcription_thread.quit
        )

        #
        # Erreur.
        #
        self.transcription_worker.error.connect(
            self.transcription_error
        )

        self.transcription_worker.error.connect(
            self.transcription_thread.quit
        )

        #
        # Nettoyage Qt.
        #
        self.transcription_thread.finished.connect(
            self.transcription_worker.deleteLater
        )

        self.transcription_thread.finished.connect(
            self.cleanup_transcription
        )

        #
        # Afficher avant le démarrage.
        #
        self.progress_dialog.show()
        self.transcription_thread.start()

    def cleanup_transcription(
        self
    ):
        self.transcription_thread = None
        self.transcription_worker = None

