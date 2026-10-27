# ui/etude_window.py
"""
Page Étude (P14.3) : vue d'ensemble d'une étude.

Réunions dans l'ordre de lecture, statuts, ordre
modifiable, ajout de réunions (projets v1 existants,
jamais modifiés), retrait, relocalisation guidée et
ouverture d'une réunion dans l'éditeur existant.

Un projet v1 introuvable n'empêche pas l'ouverture :
l'étude s'affiche en mode dégradé (réunions
joignables uniquement).
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from services.etude_io import (
    EtudeError,
    EtudeOuverte,
    ajouter_reunion,
    deplacer_reunion,
    fichier_projet_v1,
    ouvrir_etude,
    relocaliser_reunion,
    retirer_reunion,
    sauvegarder_etude,
)
from services.etude_schema import EtudeFormatError
from services.project_io import load_project
from services.settings import SettingsManager


class EtudeWindow(QWidget):

    def __init__(self, dossier_etude):
        super().__init__()

        self.settings = SettingsManager()

        self.etude = None

        try:
            self.etude = ouvrir_etude(dossier_etude)
        except EtudeFormatError as e:
            QMessageBox.critical(
                None,
                "Étude illisible",
                f"L'étude n'a pas pu être ouverte :\n\n{e}"
            )
            raise

        self.editor = None

        self.setWindowTitle(
            f"Étude — {self.etude.etude.titre}"
        )

        self.resize(700, 500)

        self.build_ui()

        self.settings.add_recent_etude(
            self.etude.dossier
        )

        self.refresh_reunions()

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(10)

        #
        # Titre.
        #
        self.titre_label = QLabel(
            self.etude.etude.titre
        )
        self.titre_label.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        theme_libelle = {
            "livre": "Livre biblique",
            "libre": "Thème libre",
        }.get(
            self.etude.etude.theme,
            self.etude.etude.theme
        )

        self.theme_label = QLabel(theme_libelle)
        self.theme_label.setStyleSheet(
            "font-size: 12px; color: #666666;"
        )

        layout.addWidget(self.titre_label)
        layout.addWidget(self.theme_label)

        self.avertissement_label = QLabel("")
        self.avertissement_label.setStyleSheet(
            "font-size: 12px; color: #b35900;"
        )
        self.avertissement_label.setWordWrap(True)
        layout.addWidget(self.avertissement_label)

        #
        # Réunions.
        #
        layout.addWidget(QLabel("Réunions"))

        self.reunions_liste = QListWidget()
        self.reunions_liste.itemDoubleClicked.connect(
            self.ouvrir_reunion_editeur
        )
        layout.addWidget(
            self.reunions_liste,
            stretch=1
        )

        boutons_reunions = QHBoxLayout()

        self.ajouter_button = QPushButton(
            "Ajouter une réunion..."
        )
        self.ajouter_button.clicked.connect(
            self.ajouter_reunion_ui
        )

        self.monter_button = QPushButton("Monter")
        self.monter_button.clicked.connect(
            self.monter_reunion
        )

        self.descendre_button = QPushButton(
            "Descendre"
        )
        self.descendre_button.clicked.connect(
            self.descendre_reunion
        )

        self.retirer_button = QPushButton(
            "Retirer la réunion"
        )
        self.retirer_button.clicked.connect(
            self.retirer_reunion_ui
        )

        self.ouvrir_button = QPushButton(
            "Ouvrir dans l'éditeur"
        )
        self.ouvrir_button.clicked.connect(
            self.ouvrir_reunion_editeur
        )

        self.relocaliser_button = QPushButton(
            "Relocaliser..."
        )
        self.relocaliser_button.clicked.connect(
            self.relocaliser_reunion_ui
        )

        for bouton in (
            self.ajouter_button,
            self.monter_button,
            self.descendre_button,
            self.retirer_button,
            self.ouvrir_button,
            self.relocaliser_button,
        ):
            boutons_reunions.addWidget(bouton)

        boutons_reunions.addStretch()

        layout.addLayout(boutons_reunions)

        #
        # Navigation.
        #
        boutons_bas = QHBoxLayout()

        self.accueil_button = QPushButton("Accueil")
        self.accueil_button.clicked.connect(
            self.retour_accueil
        )

        boutons_bas.addStretch()
        boutons_bas.addWidget(self.accueil_button)

        layout.addLayout(boutons_bas)

    def refresh_reunions(self):
        """
        Reconstitue la liste des réunions dans
        l'ordre de lecture, avec leur statut.
        """

        self.reunions_liste.clear()

        for nom in self.etude.etude.ordre_reunions:

            reunion = self.etude.reunions[nom]

            introuvable = (
                nom in self.etude.reunions_introuvables
            )

            libelle = (
                f"{reunion.numero}. "
                f"{reunion.titre_1 or nom} "
                f"({reunion.date})"
            )

            if introuvable:
                libelle += "  —  projet introuvable"

            elif reunion.resume_valide:
                libelle += "  —  résumé validé"

            item = QListWidgetItem(libelle)
            item.setData(
                Qt.ItemDataRole.UserRole,
                nom
            )

            if introuvable:
                item.setForeground(
                    Qt.GlobalColor.darkYellow
                )

            self.reunions_liste.addItem(item)

        introuvables = (
            self.etude.reunions_introuvables
        )

        if introuvables:
            self.avertissement_label.setText(
                "Mode dégradé : "
                f"{len(introuvables)} réunion(s) "
                "ont un projet v1 introuvable. "
                "Les autres réunions restent "
                "utilisables ; utilisez "
                "« Relocaliser... » après avoir "
                "sélectionné une réunion manquante."
            )
        else:
            self.avertissement_label.setText("")

    def reunion_selectionnee(self):
        """
        Nom de la réunion sélectionnée, ou None.
        """

        item = (
            self.reunions_liste.currentItem()
        )

        if item is None:
            return None

        return item.data(
            Qt.ItemDataRole.UserRole
        )

    def ajouter_reunion_ui(self):
        """
        Ajoute un projet v1 existant comme réunion
        (référence, jamais copie).
        """

        dossier, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un projet v1 (réunion)",
            self.settings.get_projects_root(),
            "Projet (*.sttproj)"
        )

        if not dossier:
            return

        try:
            nom = ajouter_reunion(
                self.etude,
                dossier
            )
        except EtudeError as e:
            QMessageBox.warning(
                self,
                "Réunion non ajoutée",
                str(e)
            )
            return

        sauvegarder_etude(self.etude)
        self.refresh_reunions()

        self.reunions_liste.setCurrentRow(
            self.etude.etude.ordre_reunions.index(nom)
        )

    def retirer_reunion_ui(self):
        """
        Retire la réunion sélectionnée de l'étude :
        sa référence et ses résultats d'étude ;
        jamais le projet v1 ni le registre FID.
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

        resultat = QMessageBox.question(
            self,
            "Retirer la réunion",
            (
                "Retirer cette réunion de l'étude ?\n\n"
                "Sa référence et ses résultats d'étude "
                "seront retirés. Le projet v1 n'est pas "
                "touché."
            )
        )

        if resultat != QMessageBox.StandardButton.Yes:
            return

        retirer_reunion(self.etude, nom)
        sauvegarder_etude(self.etude)
        self.refresh_reunions()

    def deplacer_selection(self, offset: int):
        """
        Déplace la réunion sélectionnée dans
        l'ordre de lecture.
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

        index = (
            self.etude.etude.ordre_reunions.index(nom)
        )

        try:
            deplacer_reunion(
                self.etude,
                nom,
                index + offset
            )
        except EtudeError:
            return

        sauvegarder_etude(self.etude)
        self.refresh_reunions()

        self.reunions_liste.setCurrentRow(
            self.etude.etude.ordre_reunions.index(nom)
        )

    def monter_reunion(self):
        self.deplacer_selection(-1)

    def descendre_reunion(self):
        self.deplacer_selection(1)

    def relocaliser_reunion_ui(self):
        """
        Relocalisation guidée d'une réunion au
        projet v1 introuvable.
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

        dossier, _ = QFileDialog.getOpenFileName(
            self,
            (
                "Relocaliser le projet de la réunion "
                f"« {nom} »"
            ),
            "",
            "Projet (*.sttproj)"
        )

        if not dossier:
            return

        try:
            relocaliser_reunion(
                self.etude,
                nom,
                dossier
            )
        except EtudeError as e:
            QMessageBox.warning(
                self,
                "Relocalisation impossible",
                str(e)
            )
            return

        sauvegarder_etude(self.etude)
        self.refresh_reunions()

    def ouvrir_reunion_editeur(self, *args):
        """
        Ouvre le projet v1 de la réunion sélectionnée
        dans l'éditeur existant.
        """

        nom = self.reunion_selectionnee()

        if nom is None:
            return

        chemin = fichier_projet_v1(
            self.etude,
            nom
        )

        if chemin is None:
            QMessageBox.warning(
                self,
                "Projet introuvable",
                (
                    "Le projet v1 de cette réunion est "
                    "introuvable. Utilisez "
                    "« Relocaliser... » pour le "
                    "retouver."
                )
            )
            return

        projet = load_project(str(chemin))

        from ui.main_window import MainWindow

        self.editor = MainWindow(projet)
        self.editor.show()

    def retour_accueil(self):
        """
        Sauvegarde l'étude et revient à l'accueil.
        """

        sauvegarder_etude(self.etude)

        from ui.home_window import HomeWindow

        self.accueil = HomeWindow()
        self.accueil.show()

        self.close()
