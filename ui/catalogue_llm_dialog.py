# ui/catalogue_llm_dialog.py
"""
Éditeur du catalogue LLM (P15.2).

Le catalogue est embarqué et extensible : ajouter
un fournisseur (id, famille, base URL, modèles), un
modèle (id, capacités, prix), mettre les prix à
jour — c'est le « catalogue de coûts » du contrat
format étude. Réinitialiser reconstitue les
fournisseurs par défaut sans perdre les ajouts de
l'utilisateur (règle d'invariance 3).

Les clés API ne vivent pas ici : une clé par
fournisseur, dans le CredentialStore.
"""

import copy

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from services.llm.catalogue import (
    FAMILLES_API,
    ORIGINE_UTILISATEUR,
    CatalogueError,
    CatalogueLLM,
    FournisseurCatalogue,
    ModeleCatalogue,
    catalogue_par_defaut,
    enregistrer_catalogue,
    valider_catalogue,
)


class CatalogueLLMDialog(QDialog):
    """
    Édition du catalogue : fournisseurs à gauche,
    champs du fournisseur et de ses modèles à
    droite. Enregistrer valide puis persiste le
    catalogue dans le dossier de paramétrage.
    """

    def __init__(
        self,
        parent=None,
        catalogue: CatalogueLLM = None
    ):
        super().__init__(parent)

        self.setWindowTitle("Catalogue des fournisseurs LLM")

        self.resize(760, 520)

        if catalogue is None:
            from services.llm.catalogue import (
                charger_catalogue
            )

            catalogue = charger_catalogue()

        self.catalogue = copy.deepcopy(catalogue)

        self.fournisseur_courant = None
        self.modele_courant = None

        self.build_ui()

        self.remplir_fournisseurs()

    #
    # Construction de l'interface.
    #

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        corps = QHBoxLayout()
        corps.setSpacing(10)

        #
        # Colonne fournisseurs.
        #
        colonne_gauche = QVBoxLayout()
        colonne_gauche.setSpacing(6)

        colonne_gauche.addWidget(
            QLabel("Fournisseurs")
        )

        self.liste_fournisseurs = QListWidget()
        self.liste_fournisseurs.setMinimumWidth(220)
        self.liste_fournisseurs.currentItemChanged.connect(
            self.on_fournisseur_selectionne
        )

        colonne_gauche.addWidget(
            self.liste_fournisseurs,
            stretch=1
        )

        boutons_fournisseurs = QHBoxLayout()

        self.ajouter_fournisseur_button = QPushButton(
            "Ajouter"
        )
        self.ajouter_fournisseur_button.clicked.connect(
            self.ajouter_fournisseur
        )

        self.supprimer_fournisseur_button = (
            QPushButton("Supprimer")
        )
        self.supprimer_fournisseur_button.clicked.connect(
            self.supprimer_fournisseur
        )

        boutons_fournisseurs.addWidget(
            self.ajouter_fournisseur_button
        )

        boutons_fournisseurs.addWidget(
            self.supprimer_fournisseur_button
        )

        colonne_gauche.addLayout(boutons_fournisseurs)

        corps.addLayout(colonne_gauche, stretch=1)

        #
        # Colonne détails.
        #
        colonne_droite = QVBoxLayout()
        colonne_droite.setSpacing(6)

        self.formulaire_fournisseur = QFormLayout()
        self.formulaire_fournisseur.setSpacing(6)

        self.nom_edit = QLineEdit()
        self.nom_edit.textChanged.connect(
            self.on_champ_fournisseur_change
        )

        self.famille_combo = QComboBox()
        self.famille_combo.addItems(FAMILLES_API)
        self.famille_combo.currentTextChanged.connect(
            self.on_champ_fournisseur_change
        )

        self.base_url_edit = QLineEdit()
        self.base_url_edit.textChanged.connect(
            self.on_champ_fournisseur_change
        )

        self.endpoint_combo = QComboBox()
        self.endpoint_combo.addItem(
            "Aucune info de compte",
            "none"
        )
        self.endpoint_combo.addItem(
            "Infos de compte disponibles",
            "available"
        )
        self.endpoint_combo.currentIndexChanged.connect(
            self.on_champ_fournisseur_change
        )

        self.formulaire_fournisseur.addRow(
            "Nom affiché",
            self.nom_edit
        )
        self.formulaire_fournisseur.addRow(
            "Famille d'API",
            self.famille_combo
        )
        self.formulaire_fournisseur.addRow(
            "Base URL",
            self.base_url_edit
        )
        self.formulaire_fournisseur.addRow(
            "Compte",
            self.endpoint_combo
        )

        colonne_droite.addLayout(
            self.formulaire_fournisseur
        )

        colonne_droite.addWidget(
            QLabel("Modèles (capacités et prix)")
        )

        self.liste_modeles = QListWidget()
        self.liste_modeles.currentItemChanged.connect(
            self.on_modele_selectionne
        )

        colonne_droite.addWidget(
            self.liste_modeles,
            stretch=1
        )

        self.formulaire_modele = QFormLayout()
        self.formulaire_modele.setSpacing(6)

        self.modele_id_edit = QLineEdit()
        self.modele_id_edit.textChanged.connect(
            self.on_champ_modele_change
        )

        self.modele_nom_edit = QLineEdit()
        self.modele_nom_edit.textChanged.connect(
            self.on_champ_modele_change
        )

        self.prix_in_spin = QDoubleSpinBox()
        self.prix_in_spin.setDecimals(3)
        self.prix_in_spin.setMaximum(10000.0)
        self.prix_in_spin.valueChanged.connect(
            self.on_champ_modele_change
        )

        self.prix_out_spin = QDoubleSpinBox()
        self.prix_out_spin.setDecimals(3)
        self.prix_out_spin.setMaximum(10000.0)
        self.prix_out_spin.valueChanged.connect(
            self.on_champ_modele_change
        )

        self.temperature_check = QCheckBox(
            "Température supportée"
        )
        self.temperature_check.toggled.connect(
            self.on_champ_modele_change
        )

        self.contexte_spin = QSpinBox()
        self.contexte_spin.setMaximum(10_000_000)
        self.contexte_spin.setSpecialValueText(
            "Contexte inconnu"
        )
        self.contexte_spin.valueChanged.connect(
            self.on_champ_modele_change
        )

        self.formulaire_modele.addRow(
            "Identifiant du modèle",
            self.modele_id_edit
        )
        self.formulaire_modele.addRow(
            "Nom affiché",
            self.modele_nom_edit
        )
        self.formulaire_modele.addRow(
            "Prix entrée ($ / million tokens)",
            self.prix_in_spin
        )
        self.formulaire_modele.addRow(
            "Prix sortie ($ / million tokens)",
            self.prix_out_spin
        )
        self.formulaire_modele.addRow(
            "",
            self.temperature_check
        )
        self.formulaire_modele.addRow(
            "Contexte maximal (tokens)",
            self.contexte_spin
        )

        colonne_droite.addLayout(self.formulaire_modele)

        boutons_modeles = QHBoxLayout()

        self.ajouter_modele_button = QPushButton(
            "Ajouter un modèle"
        )
        self.ajouter_modele_button.clicked.connect(
            self.ajouter_modele
        )

        self.supprimer_modele_button = QPushButton(
            "Supprimer le modèle"
        )
        self.supprimer_modele_button.clicked.connect(
            self.supprimer_modele
        )

        boutons_modeles.addWidget(
            self.ajouter_modele_button
        )

        boutons_modeles.addWidget(
            self.supprimer_modele_button
        )

        boutons_modeles.addStretch()

        colonne_droite.addLayout(boutons_modeles)

        corps.addLayout(colonne_droite, stretch=2)

        layout.addLayout(corps, stretch=1)

        #
        # Actions du bas.
        #
        actions = QHBoxLayout()

        self.reinitialiser_button = QPushButton(
            "Réinitialiser les valeurs par défaut"
        )
        self.reinitialiser_button.setToolTip(
            "Reconstitue les fournisseurs par défaut "
            "sans perdre ceux que vous avez ajoutés"
        )
        self.reinitialiser_button.clicked.connect(
            self.reinitialiser_defauts
        )

        self.annuler_button = QPushButton("Annuler")
        self.annuler_button.clicked.connect(self.reject)

        self.enregistrer_button = QPushButton(
            "Enregistrer"
        )
        self.enregistrer_button.clicked.connect(
            self.enregistrer
        )

        actions.addWidget(self.reinitialiser_button)
        actions.addStretch()
        actions.addWidget(self.annuler_button)
        actions.addWidget(self.enregistrer_button)

        layout.addLayout(actions)

    #
    # Fournisseurs.
    #

    def remplir_fournisseurs(self):

        self.liste_fournisseurs.blockSignals(True)
        self.liste_fournisseurs.clear()

        for fournisseur in self.catalogue.fournisseurs:

            etiquette = fournisseur.nom

            if (
                fournisseur.origine
                == ORIGINE_UTILISATEUR
            ):
                etiquette += "  (ajouté)"

            item = QListWidgetItem(etiquette)
            item.setData(
                Qt.ItemDataRole.UserRole,
                fournisseur.id
            )

            self.liste_fournisseurs.addItem(item)

        self.liste_fournisseurs.blockSignals(False)

        if self.catalogue.fournisseurs:
            self.liste_fournisseurs.setCurrentRow(0)
        else:
            self.fournisseur_courant = None
            self.vider_champs_fournisseur()
            self.vider_champs_modele()
            self.liste_modeles.blockSignals(True)
            self.liste_modeles.clear()
            self.liste_modeles.blockSignals(False)

    def on_fournisseur_selectionne(
        self,
        courant,
        _precedent
    ):

        self.appliquer_champs_fournisseur()
        self.appliquer_champs_modele()

        if courant is None:
            self.fournisseur_courant = None
            return

        fournisseur_id = courant.data(
            Qt.ItemDataRole.UserRole
        )

        self.fournisseur_courant = (
            self.catalogue.chercher_fournisseur(
                fournisseur_id
            )
        )

        self.remplir_champs_fournisseur()
        self.remplir_modeles()

    def remplir_champs_fournisseur(self):

        fournisseur = self.fournisseur_courant

        if fournisseur is None:
            self.vider_champs_fournisseur()
            return

        self.nom_edit.setText(fournisseur.nom)
        self.famille_combo.setCurrentText(
            fournisseur.famille_api
        )
        self.base_url_edit.setText(fournisseur.base_url)

        index = self.endpoint_combo.findData(
            fournisseur.endpoint_infos_compte
        )

        if index >= 0:
            self.endpoint_combo.setCurrentIndex(index)

    def vider_champs_fournisseur(self):

        self.nom_edit.setText("")
        self.base_url_edit.setText("")

    def on_champ_fournisseur_change(self, *args):

        fournisseur = self.fournisseur_courant

        if fournisseur is None:
            return

        fournisseur.nom = self.nom_edit.text()
        fournisseur.famille_api = (
            self.famille_combo.currentText()
        )
        fournisseur.base_url = (
            self.base_url_edit.text()
        )
        fournisseur.endpoint_infos_compte = (
            self.endpoint_combo.currentData()
        )

        # Rafraichir l'etiquette de la liste.
        ligne = self.liste_fournisseurs.currentRow()

        item = self.liste_fournisseurs.item(ligne)

        if item is not None:

            etiquette = fournisseur.nom

            if (
                fournisseur.origine
                == ORIGINE_UTILISATEUR
            ):
                etiquette += "  (ajouté)"

            item.setText(etiquette)

    def ajouter_fournisseur(self):

        self.appliquer_champs_fournisseur()
        self.appliquer_champs_modele()

        base = "nouveau_fournisseur"
        identifiant = base
        compteur = 1

        while (
            self.catalogue.chercher_fournisseur(
                identifiant
            )
            is not None
        ):
            compteur += 1
            identifiant = f"{base}_{compteur}"

        fournisseur = FournisseurCatalogue(
            id=identifiant,
            nom="Nouveau fournisseur",
            famille_api="openai_compatible",
            base_url="http://localhost:11434/v1",
            endpoint_infos_compte="none",
            origine=ORIGINE_UTILISATEUR,
        )

        self.catalogue.ajouter_fournisseur(fournisseur)

        self.remplir_fournisseurs()

        index = self.liste_fournisseurs.count() - 1
        self.liste_fournisseurs.setCurrentRow(index)

    def supprimer_fournisseur(self):

        if self.fournisseur_courant is None:
            return

        nom = self.fournisseur_courant.nom

        resultat = QMessageBox.question(
            self,
            "Supprimer le fournisseur",
            (
                f"Supprimer {nom} du catalogue ?\n\n"
                "Les clés API éventuellement "
                "enregistrées pour ce fournisseur "
                "resteront dans le CredentialStore "
                "(sans effet)."
            )
        )

        if (
            resultat
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.catalogue.fournisseurs.remove(
            self.fournisseur_courant
        )

        self.remplir_fournisseurs()

    #
    # Modèles.
    #

    def remplir_modeles(self):

        self.liste_modeles.blockSignals(True)
        self.liste_modeles.clear()

        fournisseur = self.fournisseur_courant

        if fournisseur is not None:

            for modele in fournisseur.modeles:

                item = QListWidgetItem(modele.nom_affiche)
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    modele.id
                )

                self.liste_modeles.addItem(item)

        self.liste_modeles.blockSignals(False)

        if fournisseur and fournisseur.modeles:
            self.liste_modeles.setCurrentRow(0)
        else:
            self.modele_courant = None
            self.vider_champs_modele()

    def on_modele_selectionne(
        self,
        courant,
        _precedent
    ):

        self.appliquer_champs_modele()

        if courant is None:
            self.modele_courant = None
            return

        fournisseur = self.fournisseur_courant

        if fournisseur is None:
            return

        modele_id = courant.data(
            Qt.ItemDataRole.UserRole
        )

        self.modele_courant = (
            fournisseur.chercher_modele(modele_id)
        )

        self.remplir_champs_modele()

    def remplir_champs_modele(self):

        modele = self.modele_courant

        if modele is None:
            self.vider_champs_modele()
            return

        self.modele_id_edit.setText(modele.id)
        self.modele_nom_edit.setText(modele.nom_affiche)
        self.prix_in_spin.setValue(
            float(modele.prix.get("in_par_million", 0.0))
        )
        self.prix_out_spin.setValue(
            float(modele.prix.get("out_par_million", 0.0))
        )
        self.temperature_check.setChecked(
            bool(modele.capacites.get("temperature"))
        )

        contexte = modele.capacites.get(
            "max_contexte_tokens",
            0
        )

        self.contexte_spin.setValue(
            int(contexte) if contexte else 0
        )

    def vider_champs_modele(self):

        self.modele_id_edit.setText("")
        self.modele_nom_edit.setText("")
        self.prix_in_spin.setValue(0.0)
        self.prix_out_spin.setValue(0.0)
        self.temperature_check.setChecked(False)
        self.contexte_spin.setValue(0)

    def on_champ_modele_change(self, *args):

        modele = self.modele_courant

        if modele is None:
            return

        modele.id = self.modele_id_edit.text()
        modele.nom_affiche = (
            self.modele_nom_edit.text()
            or modele.id
        )
        modele.prix["in_par_million"] = (
            self.prix_in_spin.value()
        )
        modele.prix["out_par_million"] = (
            self.prix_out_spin.value()
        )

        if self.temperature_check.isChecked():
            modele.capacites["temperature"] = True
        else:
            modele.capacites.pop("temperature", None)

        if self.contexte_spin.value() > 0:
            modele.capacites[
                "max_contexte_tokens"
            ] = self.contexte_spin.value()
        else:
            modele.capacites.pop(
                "max_contexte_tokens",
                None
            )

        ligne = self.liste_modeles.currentRow()

        item = self.liste_modeles.item(ligne)

        if item is not None:
            item.setText(modele.nom_affiche)

    def appliquer_champs_fournisseur(self):
        """
        Garde-fou : rien à appliquer, les champs
        écrivent directement dans l'objet courant.
        """

        pass

    def appliquer_champs_modele(self):
        """
        Garde-fou : rien à appliquer, les champs
        écrivent directement dans l'objet courant.
        """

        pass

    def ajouter_modele(self):

        fournisseur = self.fournisseur_courant

        if fournisseur is None:
            return

        base = "nouveau_modele"
        identifiant = base
        compteur = 1

        while (
            fournisseur.chercher_modele(identifiant)
            is not None
        ):
            compteur += 1
            identifiant = f"{base}_{compteur}"

        modele = ModeleCatalogue(
            id=identifiant,
            nom_affiche="Nouveau modèle",
            capacites={"temperature": True},
            prix={
                "in_par_million": 0.0,
                "out_par_million": 0.0,
            },
            origine=ORIGINE_UTILISATEUR,
        )

        fournisseur.modeles.append(modele)

        self.remplir_modeles()

        index = self.liste_modeles.count() - 1
        self.liste_modeles.setCurrentRow(index)

    def supprimer_modele(self):

        fournisseur = self.fournisseur_courant
        modele = self.modele_courant

        if (
            fournisseur is None
            or modele is None
        ):
            return

        fournisseur.modeles.remove(modele)

        self.remplir_modeles()

    #
    # Réinitialisation et enregistrement.
    #

    def reinitialiser_defauts(self):
        """
        Règle d'invariance 3 : reconstituer les
        fournisseurs par défaut sans perdre les
        ajouts de l'utilisateur.
        """

        resultat = QMessageBox.question(
            self,
            "Réinitialiser les valeurs par défaut",
            (
                "Reconstituer les fournisseurs par "
                "défaut (OpenAI, Mistral, Anthropic) ?\n\n"
                "Les fournisseurs que vous avez "
                "ajoutés et leurs modèles seront "
                "conservés. Les prix modifiés des "
                "modèles par défaut reviendront aux "
                "valeurs embarquées."
            )
        )

        if (
            resultat
            != QMessageBox.StandardButton.Yes
        ):
            return

        defauts = catalogue_par_defaut()

        conservees = [
            fournisseur
            for fournisseur
            in self.catalogue.fournisseurs
            if (
                fournisseur.origine
                == ORIGINE_UTILISATEUR
            )
        ]

        self.catalogue = CatalogueLLM(
            catalogue_version=(
                defauts.catalogue_version
            ),
            fournisseurs=(
                list(defauts.fournisseurs)
                + conservees
            ),
        )

        self.fournisseur_courant = None
        self.modele_courant = None

        self.remplir_fournisseurs()

    def enregistrer(self):

        try:
            valider_catalogue(self.catalogue)

        except CatalogueError as e:
            QMessageBox.critical(
                self,
                "Catalogue invalide",
                str(e)
            )
            return

        try:
            enregistrer_catalogue(self.catalogue)

        except OSError as e:
            QMessageBox.critical(
                self,
                "Enregistrement impossible",
                str(e)
            )
            return

        self.accept()
