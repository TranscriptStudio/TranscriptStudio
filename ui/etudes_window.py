# ui/etudes_window.py
"""
Vue Études (P18.6-bis, spec correctifs §4) :
la tuile « Études » du hub ouvre cette vue
dédiée — le hub reste épuré (bandeau,
salutation, 3 tuiles, dernières réunions) et
n'affiche JAMAIS la liste des études
(invariant complémentaire 1).

Liste des études récentes, « Nouvelle étude »,
« Ouvrir depuis un dossier… ».
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.etude_io import (
    EtudeError,
    creer_etude,
)
from services.help import open_user_manual
from services.settings import SettingsManager


class EtudesWindow(QWidget):
    """
    Vue dédiée des études : liste, création,
    ouverture.
    """

    def __init__(self, settings=None):
        super().__init__()

        self.settings = (
            settings
            if settings is not None
            else SettingsManager()
        )

        self.build_ui()

        self.refresh_etudes()

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        #
        # Ruban (pas de bandeau app hors accueil —
        # invariant §9.2).
        #
        ruban = QWidget()
        ruban.setObjectName("ruban_etudes")

        ruban_layout = QHBoxLayout(ruban)
        ruban_layout.setContentsMargins(0, 0, 0, 0)
        ruban_layout.setSpacing(10)

        titre = QLabel("Études")
        titre.setStyleSheet(
            "font-size: 18px; font-weight: 600;"
        )

        ruban_layout.addWidget(titre)
        ruban_layout.addStretch()

        self.accueil_button = QPushButton(
            "Accueil"
        )
        self.accueil_button.clicked.connect(
            self.ouvrir_accueil
        )

        self.parametres_button = QPushButton(
            "⚙ Paramètres"
        )
        self.parametres_button.clicked.connect(
            self.ouvrir_parametres
        )

        self.aide_button = QPushButton("? Aide")
        self.aide_button.clicked.connect(
            open_user_manual
        )

        for bouton in (
            self.accueil_button,
            self.parametres_button,
            self.aide_button,
        ):
            ruban_layout.addWidget(bouton)

        layout.addWidget(ruban)

        description = QLabel(
            "Créer une étude, ouvrir et gérer une "
            "étude existante. Une étude est un "
            "regroupement de réunions ayant pour "
            "objet un thème spécifique."
        )
        description.setWordWrap(True)
        description.setStyleSheet(
            "color: #555555;"
        )

        layout.addWidget(description)
        layout.addSpacing(4)

        self.liste_etudes = QListWidget()
        self.liste_etudes.setToolTip(
            "Double-clic : ouvrir l'étude"
        )
        self.liste_etudes.itemDoubleClicked.connect(
            self.ouvrir_etude_selection
        )

        layout.addWidget(
            self.liste_etudes,
            stretch=1
        )

        actions = QHBoxLayout()

        self.nouvelle_button = QPushButton(
            "Nouvelle étude"
        )
        self.nouvelle_button.setToolTip(
            "Créer une étude regroupant des réunions"
        )
        self.nouvelle_button.clicked.connect(
            self.creer_etude_ui
        )

        self.ouvrir_dossier_button = QPushButton(
            "Ouvrir depuis un dossier…"
        )
        self.ouvrir_dossier_button.setToolTip(
            "Choisir un dossier étude sur le disque "
            "(il doit contenir un etude.json)"
        )
        self.ouvrir_dossier_button.clicked.connect(
            self.ouvrir_etude_dialogue
        )

        self.ouvrir_button = QPushButton(
            "Ouvrir l'étude sélectionnée"
        )
        self.ouvrir_button.setToolTip(
            "Ouvrir l'étude sélectionnée dans la "
            "liste : réunions, reformulation "
            "littéraire, résumé, synthèse"
        )
        self.ouvrir_button.clicked.connect(
            self.ouvrir_etude_selection
        )

        actions.addWidget(self.nouvelle_button)
        actions.addWidget(
            self.ouvrir_dossier_button
        )
        actions.addWidget(self.ouvrir_button)
        actions.addStretch()

        layout.addLayout(actions)

    # ==================================================
    # Liste.
    # ==================================================

    def refresh_etudes(self):

        self.liste_etudes.clear()

        for etude_folder in (
            self.settings.cleanup_recent_etudes()
        ):

            dossier = Path(etude_folder)

            item = QListWidgetItem(dossier.name)
            item.setData(
                0x0100,  # Qt.ItemDataRole.UserRole
                str(dossier)
            )
            item.setToolTip(str(dossier))

            self.liste_etudes.addItem(item)

    # ==================================================
    # Ouverture et création.
    # ==================================================

    def ouvrir_etude(self, dossier):
        """
        Ouvre la page Étude via la pile de
        navigation (repli : fenêtre autonome pour
        les tests/lancement direct).
        """

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if navigation is not None:
            navigation.ouvrir_etude(dossier)
            return

        from services.etude_schema import (
            EtudeFormatError
        )
        from ui.etude_window import EtudeWindow

        try:
            self.fenetre_etude = EtudeWindow(
                dossier,
                settings=self.settings
            )
        except EtudeFormatError:
            return

        self.fenetre_etude.show()

    def ouvrir_etude_selection(self, *args):

        item = (
            self.liste_etudes.currentItem()
        )

        if item is None:
            QMessageBox.information(
                self,
                "Aucune étude sélectionnée",
                "Sélectionnez d'abord une étude dans "
                "la liste."
            )
            return

        dossier = item.data(0x0100)

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
            self.refresh_etudes()
            return

        self.ouvrir_etude(dossier)

    def creer_etude_ui(self):
        """
        Crée une étude : choix du dossier, titre,
        structure complète du format étude.

        Dossier non vide autorisé avec confirmation
        explicite ; dossier déjà étude : refus dur
        avec ouverture proposée
        (ARBITRAGE_CREATION_ETUDE).
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
        « Ouvrir depuis un dossier… » : sélection
        d'un dossier, validation de la présence d'un
        etude.json (sinon message clair, rien ne
        s'ouvre), ouverture.
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

    # ==================================================
    # Navigation.
    # ==================================================

    def ouvrir_accueil(self):

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if navigation is not None:
            navigation.ouvrir_accueil()

    def ouvrir_parametres(self):

        from ui.settings_dialog import SettingsDialog

        dialogue = SettingsDialog(
            self,
            settings=self.settings
        )

        if dialogue.exec():
            self.settings.load()
