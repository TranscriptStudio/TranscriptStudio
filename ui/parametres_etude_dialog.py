# ui/parametres_etude_dialog.py
"""
Paramètres de l'étude (P16.1).

Contrat §10 : les prompts stockés sont les valeurs
**actives** de l'étude (initialisés depuis les v2 de
référence, éditables ici) ; modèle et température
surchargeables par étude ; interdits stylistiques
(§5.3) éditables.

Aucune clé API : elles vivent dans le CredentialStore.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from services.controle_qualite import (
    INTERDITS_STYLISTIQUES_DEFAUT,
)
from services.bibles import (
    VERSIONS_BIBLE,
    version_bible_etude,
    version_installee,
)
from services.etude_io import (
    EtudeOuverte,
    sauvegarder_etude,
)


class ParametresEtudeDialog(QDialog):
    """
    Édition des paramètres actifs de l'étude :
    prompts v2, modèles, températures, fenêtre
    glissante, longueur cible du résumé, interdits
    stylistiques.
    """

    def __init__(
        self,
        etude_ouverte: EtudeOuverte,
        parent=None
    ):
        super().__init__(parent)

        self.etude = etude_ouverte

        self.setWindowTitle(
            "Paramètres de l'étude"
        )

        self.resize(720, 640)

        self.build_ui()

        self.charger_valeurs()

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        reformulation = self._onglet_reformulation()
        resume = self._onglet_resume()
        bible = self._bloc_bible()

        for onglet in (reformulation, resume, bible):
            layout.addWidget(onglet)

        interdits_label = QLabel(
            "Interdits stylistiques (contrôle qualité, "
            "un motif par ligne — liste éditable)"
        )
        layout.addWidget(interdits_label)

        self.interdits_edit = QPlainTextEdit()
        self.interdits_edit.setMaximumHeight(80)
        layout.addWidget(self.interdits_edit)

        boutons = QHBoxLayout()
        boutons.addStretch()

        self.annuler_button = QPushButton("Annuler")
        self.annuler_button.clicked.connect(self.reject)

        self.enregistrer_button = QPushButton(
            "Enregistrer"
        )
        self.enregistrer_button.clicked.connect(
            self.enregistrer
        )

        boutons.addWidget(self.annuler_button)
        boutons.addWidget(self.enregistrer_button)

        layout.addLayout(boutons)

    def _onglet_reformulation(self) -> QWidget:
        """
        Bloc Reformulation : prompt actif (v2 de
        référence, éditable), modèle surchargé,
        température, fenêtre glissante.
        """

        bloc = QWidget()

        formulaire = QFormLayout(bloc)
        formulaire.setContentsMargins(0, 8, 0, 8)
        formulaire.setSpacing(8)

        titre = QLabel("<b>Bloc Reformulation</b>")
        formulaire.addRow(titre)

        self.prompt_reformulation_edit = (
            QPlainTextEdit()
        )

        self.prompt_reformulation_edit.setPlaceholderText(
            "Prompt système actif du bloc "
            "(valeur par défaut : prompt v2)"
        )

        formulaire.addRow(
            "Prompt système",
            self.prompt_reformulation_edit
        )

        self.modele_reformulation_edit = QLineEdit()
        self.modele_reformulation_edit.setToolTip(
            "Modèle surchargé pour cette étude "
            "(les réglages de l'app font foi s'il "
            "n'existe pas chez le fournisseur configuré)"
        )
        formulaire.addRow(
            "Modèle",
            self.modele_reformulation_edit
        )

        self.temperature_reformulation_spin = (
            QDoubleSpinBox()
        )
        self.temperature_reformulation_spin.setRange(
            0.0, 2.0
        )
        self.temperature_reformulation_spin.setDecimals(2)
        self.temperature_reformulation_spin.setSingleStep(0.1)
        self.temperature_reformulation_spin.setToolTip(
            "Basse (0.2) : sobre et fidèle. "
            "Haute : plus libre. Défaut : 0.3."
        )
        formulaire.addRow(
            "Température",
            self.temperature_reformulation_spin
        )

        self.fenetre_spin = QSpinBox()
        self.fenetre_spin.setRange(200, 100_000)
        self.fenetre_spin.setSingleStep(100)
        self.fenetre_spin.setToolTip(
            "Taille maximale de la fenêtre glissante "
            "de contexte (~2 000 tokens par défaut)"
        )
        formulaire.addRow(
            "Fenêtre glissante (tokens)",
            self.fenetre_spin
        )

        #
        # Cases de contexte du bloc (P17.2) : la
        # synthèse d'étude sert aux blocs qui le
        # cochent.
        #
        self.contexte_fenetre_check = QCheckBox(
            "Envoyer les reformulations précédentes "
            "en contexte (fenêtre glissante)"
        )
        formulaire.addRow(self.contexte_fenetre_check)

        self.contexte_synthese_check = QCheckBox(
            "Envoyer la synthèse d'étude en contexte"
        )
        self.contexte_synthese_check.setToolTip(
            "Générée à la validation complète d'une "
            "réunion, régénérable depuis la page Étude."
        )
        formulaire.addRow(self.contexte_synthese_check)

        return bloc

    def _onglet_resume(self) -> QWidget:
        """
        Bloc Résumé (valeurs actives ; exécution en P17).
        """

        bloc = QWidget()

        formulaire = QFormLayout(bloc)
        formulaire.setContentsMargins(0, 8, 0, 8)
        formulaire.setSpacing(8)

        titre = QLabel("<b>Bloc Résumé</b>")
        formulaire.addRow(titre)

        self.prompt_resume_edit = QPlainTextEdit()
        self.prompt_resume_edit.setPlaceholderText(
            "Prompt système actif du résumé "
            "(valeur par défaut : prompt v2)"
        )
        formulaire.addRow(
            "Prompt système",
            self.prompt_resume_edit
        )

        self.modele_resume_edit = QLineEdit()
        formulaire.addRow(
            "Modèle",
            self.modele_resume_edit
        )

        self.temperature_resume_spin = QDoubleSpinBox()
        self.temperature_resume_spin.setRange(
            0.0, 2.0
        )
        self.temperature_resume_spin.setDecimals(2)
        self.temperature_resume_spin.setSingleStep(0.1)
        self.temperature_resume_spin.setToolTip(
            "Basse (0.2) : sobre et fidèle. Défaut : 0.2."
        )
        formulaire.addRow(
            "Température",
            self.temperature_resume_spin
        )

        longueur_widget = QWidget()
        longueur_layout = QHBoxLayout(longueur_widget)
        longueur_layout.setContentsMargins(0, 0, 0, 0)
        longueur_layout.setSpacing(6)

        self.longueur_min_spin = QSpinBox()
        self.longueur_min_spin.setRange(100, 5000)
        self.longueur_min_spin.setSingleStep(50)

        self.longueur_max_spin = QSpinBox()
        self.longueur_max_spin.setRange(100, 5000)
        self.longueur_max_spin.setSingleStep(50)

        longueur_layout.addWidget(self.longueur_min_spin)
        longueur_layout.addWidget(QLabel("à"))
        longueur_layout.addWidget(self.longueur_max_spin)
        longueur_layout.addWidget(QLabel("mots"))

        formulaire.addRow(
            "Longueur cible",
            longueur_widget
        )

        self.source_defaut_combo = QComboBox()
        self.source_defaut_combo.addItem(
            "Reformulations validées (recommandé)",
            "reformulations_valides"
        )
        self.source_defaut_combo.addItem(
            "Transcription brute corrigée",
            "brute_corrigee"
        )
        formulaire.addRow(
            "Source par défaut",
            self.source_defaut_combo
        )

        return bloc

    def _bloc_bible(self) -> QWidget:
        """
        Bloc Bible (P18.5, spec §3) : version retenue
        par l'étude (bloc ``bible`` de parametres.json,
        défaut darbyR) — le contrôle qualité travaille
        toujours contre cette version.
        """

        bloc = QWidget()

        formulaire = QFormLayout(bloc)
        formulaire.setContentsMargins(0, 8, 0, 8)
        formulaire.setSpacing(8)

        titre = QLabel("<b>Bible de référence</b>")
        formulaire.addRow(titre)

        self.version_bible_combo = QComboBox()

        for identifiant in VERSIONS_BIBLE:

            version = VERSIONS_BIBLE[identifiant]

            etat = (
                "installée"
                if version_installee(identifiant)
                else "non installée"
            )

            self.version_bible_combo.addItem(
                f"{version['nom']} — {etat}",
                identifiant
            )

        self.version_bible_combo.setToolTip(
            "Version utilisée par le contrôle qualité "
            "(références et citations) pour cette "
            "étude. Les versions s'installent depuis "
            "les réglages de l'application, onglet "
            "« Bibles »."
        )

        formulaire.addRow(
            "Version retenue",
            self.version_bible_combo
        )

        return bloc

    def charger_valeurs(self):
        """
        Charge les valeurs actives de l'étude.
        """

        reformulation = self.etude.parametres.reformulation
        resume = self.etude.parametres.resume

        self.prompt_reformulation_edit.setPlainText(
            reformulation.get("prompt", "")
        )

        self.modele_reformulation_edit.setText(
            reformulation.get("modele", "") or ""
        )

        self.temperature_reformulation_spin.setValue(
            float(
                reformulation.get("temperature") or 0.3
            )
        )

        self.fenetre_spin.setValue(
            int(
                reformulation.get(
                    "fenetre_glissante_tokens"
                ) or 2000
            )
        )

        contexte = reformulation.get("contexte") or {}

        self.contexte_fenetre_check.setChecked(
            bool(contexte.get("fenetre_glissante", True))
        )

        self.contexte_synthese_check.setChecked(
            bool(contexte.get("synthese_etude", True))
        )

        self.prompt_resume_edit.setPlainText(
            resume.get("prompt", "")
        )

        self.modele_resume_edit.setText(
            resume.get("modele", "") or ""
        )

        self.temperature_resume_spin.setValue(
            float(resume.get("temperature") or 0.2)
        )

        longueur = resume.get("longueur_cible_mots") or [
            650, 700
        ]

        self.longueur_min_spin.setValue(int(longueur[0]))
        self.longueur_max_spin.setValue(int(longueur[1]))

        index = self.source_defaut_combo.findData(
            resume.get(
                "source_defaut",
                "reformulations_valides"
            )
        )

        self.source_defaut_combo.setCurrentIndex(
            max(0, index)
        )

        index_bible = self.version_bible_combo.findData(
            version_bible_etude(self.etude.parametres)
        )

        self.version_bible_combo.setCurrentIndex(
            max(0, index_bible)
        )

        interdits = (
            self.etude.parametres.controle_qualite.get(
                "interdits_stylistiques"
            )
        )

        if interdits is None:
            interdits = INTERDITS_STYLISTIQUES_DEFAUT

        self.interdits_edit.setPlainText(
            "\n".join(interdits)
        )

    def enregistrer(self):
        """
        Écrit les valeurs actives dans les paramètres
        de l'étude et sauvegarde.
        """

        reformulation = (
            self.etude.parametres.reformulation
        )

        reformulation["prompt"] = (
            self.prompt_reformulation_edit.toPlainText()
        )

        reformulation["modele"] = (
            self.modele_reformulation_edit.text().strip()
            or None
        )

        reformulation["temperature"] = (
            self.temperature_reformulation_spin.value()
        )

        reformulation[
            "fenetre_glissante_tokens"
        ] = self.fenetre_spin.value()

        reformulation.setdefault("contexte", {})

        reformulation["contexte"][
            "fenetre_glissante"
        ] = self.contexte_fenetre_check.isChecked()

        reformulation["contexte"][
            "synthese_etude"
        ] = self.contexte_synthese_check.isChecked()

        resume = self.etude.parametres.resume

        resume["prompt"] = self.prompt_resume_edit.toPlainText()

        resume["modele"] = (
            self.modele_resume_edit.text().strip() or None
        )

        resume["temperature"] = (
            self.temperature_resume_spin.value()
        )

        resume["longueur_cible_mots"] = [
            self.longueur_min_spin.value(),
            self.longueur_max_spin.value()
        ]

        resume["source_defaut"] = (
            self.source_defaut_combo.currentData()
        )

        version_bible = (
            self.version_bible_combo.currentData()
        )

        self.etude.parametres.bible["version"] = (
            version_bible
        )

        interdits = [
            ligne.strip()
            for ligne in self.interdits_edit.toPlainText().splitlines()
            if ligne.strip()
        ]

        self.etude.parametres.controle_qualite[
            "interdits_stylistiques"
        ] = interdits

        sauvegarder_etude(self.etude)

        if not version_installee(version_bible):

            reponse = QMessageBox.question(
                self,
                "Bible non installée",
                "La version retenue n'est pas installée : "
                "le contrôle qualité des références et "
                "citations ne pourra pas l'utiliser.\n\n"
                "Ouvrir les réglages pour l'installer ?",
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
            )

            if reponse == (
                QMessageBox.StandardButton.Yes
            ):
                from ui.settings_dialog import SettingsDialog

                SettingsDialog(self).exec()

        self.accept()
