# ui/parametres_etude_dialog.py
"""
Paramètres de l'étude (P16.1, allégé en P18.11 —
relecture 3 du 2026-11-10, SPEC_PAGE_ETUDE_ET_
SYNTHESE_MODIFS_2026-11-10b §8, invariants 20-22).

Le dialogue n'expose QUE les champs d'étude :
bloc Général (titre, thème), options de contexte de
la reformulation (fenêtre glissante + champ tokens,
synthèse d'étude en contexte), résumé (longueur
cible, source par défaut), Bible de référence
(version + propagation P18.8c) et interdits
stylistiques.

**Plus aucun paramètre LLM ni aucun prompt** dans ce
di (P18.11b) : la surcharge d'étude des paramètres LLM
et des prompts est ABROGÉE (P18.11c) — les opérations
des réunions utilisent les paramètres du tier, la
synthèse d'étude les réglages de l'app (LLM globaux
+ prompt de la bibliothèque prompts/synthese_etude.md).
Le mécanisme ⚙ Prompts (UI_GESTION_PROMPTS_V2) reste
inchangé (P18.11e).

Aucune clé API : elles vivent dans le CredentialStore.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
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
    Édition des paramètres de l'étude — champs
    d'étude UNIQUEMENT (P18.11) : titre/thème,
    options de contexte de la reformulation, longueur
    cible et source par défaut du résumé, Bible de
    référence, interdits stylistiques. Aucun
    paramètre LLM ni prompt (surcharge d'étude
    abrogée).
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

        general = self._bloc_general()
        reformulation = self._onglet_reformulation()
        resume = self._onglet_resume()
        bible = self._bloc_bible()

        for onglet in (
            general,
            reformulation,
            resume,
            bible
        ):
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

    def _bloc_general(self) -> QWidget:
        """
        P18.8b : bloc Général — titre et thème de
        l'étude (repris de l'ancienne mini-fenêtre
        « Modifier l'étude »).
        """

        from PySide6.QtWidgets import (
            QComboBox,
            QLineEdit,
        )

        bloc = QWidget()

        formulaire = QFormLayout(bloc)
        formulaire.setContentsMargins(0, 8, 0, 8)
        formulaire.setSpacing(8)

        titre = QLabel("<b>Général</b>")
        formulaire.addRow(titre)

        self.titre_etude_edit = QLineEdit(
            self.etude.etude.titre or ""
        )

        formulaire.addRow(
            "Titre de l'étude :",
            self.titre_etude_edit
        )

        self.theme_combo = QComboBox()
        self.theme_combo.addItem(
            "Livre biblique",
            "livre"
        )
        self.theme_combo.addItem(
            "Thème libre",
            "libre"
        )

        index = self.theme_combo.findData(
            self.etude.etude.theme
        )

        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        formulaire.addRow(
            "Thème :",
            self.theme_combo
        )

        return bloc

    def _onglet_reformulation(self) -> QWidget:
        """
        P18.11 : options de contexte de la
        reformulation UNIQUEMENT — plus de prompt,
        modèle ni température (surcharge d'étude
        abrogée : les traitements d'une réunion
        utilisent les paramètres du tier).
        """

        bloc = QWidget()

        formulaire = QFormLayout(bloc)
        formulaire.setContentsMargins(0, 8, 0, 8)
        formulaire.setSpacing(8)

        titre = QLabel(
            "<b>Options de contexte de la reformulation</b>"
        )
        formulaire.addRow(titre)

        #
        # P18.11b : PLUS de zone « Prompt système »,
        # de menu « Modèle » ni de champ « Température »
        # dans ce dialogue. Conservés : la case fenêtre
        # glissante AVEC son champ « Fenêtre glissante
        # (tokens) » à côté (arbitrage David du 10/11),
        # et la case « synthèse d'étude en contexte ».
        #
        ligne_fenetre = QHBoxLayout()
        ligne_fenetre.setContentsMargins(0, 0, 0, 0)
        ligne_fenetre.setSpacing(6)

        self.contexte_fenetre_check = QCheckBox(
            "Envoyer les reformulations précédentes "
            "en contexte (fenêtre glissante)"
        )
        ligne_fenetre.addWidget(self.contexte_fenetre_check)

        self.fenetre_spin = QSpinBox()
        self.fenetre_spin.setRange(200, 100_000)
        self.fenetre_spin.setSingleStep(100)
        self.fenetre_spin.setToolTip(
            "Taille maximale de la fenêtre glissante "
            "de contexte (~2 000 tokens par défaut)"
        )
        ligne_fenetre.addWidget(
            QLabel("Fenêtre glissante (tokens)")
        )
        ligne_fenetre.addWidget(self.fenetre_spin)
        ligne_fenetre.addStretch()

        formulaire.addRow(ligne_fenetre)

        #
        # Case de contexte (P17.2) : la synthèse
        # d'étude sert aux blocs qui le cochent.
        #
        self.contexte_synthese_check = QCheckBox(
            "Envoyer la synthèse d'étude en contexte"
        )
        self.contexte_synthese_check.setToolTip(
            "La synthèse d'étude sert de contexte aux "
            "blocs qui cochent cette case."
        )
        formulaire.addRow(self.contexte_synthese_check)

        return bloc

    def _onglet_resume(self) -> QWidget:
        """
        P18.11 : bloc Résumé — longueur cible et
        source par défaut UNIQUEMENT (plus de prompt,
        modèle ni température).
        """

        bloc = QWidget()

        formulaire = QFormLayout(bloc)
        formulaire.setContentsMargins(0, 8, 0, 8)
        formulaire.setSpacing(8)

        titre = QLabel("<b>Résumé</b>")
        formulaire.addRow(titre)

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

        #
        # P18.8c (ARBITRAGE_P18_7_ECARTS écart 2, validé
        # avec exigence d'explicité) : libellé EXPLICITE —
        # jamais silencieux — indiquant que l'enregistrement
        # propage la version choisie vers les tiers des
        # réunions rattachées.
        #
        nb_reunions = len(
            self.etude.etude.ordre_reunions
        )

        self.propagation_label = QLabel(
            "À l'enregistrement, la version choisie "
            "est propagée vers les tiers des "
            f"{nb_reunions} réunion(s) rattachée(s) "
            "de l'étude."
        )
        self.propagation_label.setWordWrap(True)
        self.propagation_label.setStyleSheet(
            "color: #757575; font-size: 11px;"
        )

        formulaire.addRow(self.propagation_label)

        return bloc

    def charger_valeurs(self):
        """
        Charge les valeurs actives de l'étude.
        """

        reformulation = self.etude.parametres.reformulation
        resume = self.etude.parametres.resume

        # P18.11 : plus de prompt/modèle/température
        # chargés (ces champs n'existent plus).

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

        from services.bibles import (
            version_commune_etude,
        )

        version_courante, _mixte = version_commune_etude(
            self.etude
        )

        index_bible = self.version_bible_combo.findData(
            version_courante
            or version_bible_etude(self.etude.parametres)
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

        # P18.8b : bloc Général — titre + thème.
        titre = self.titre_etude_edit.text().strip()

        if titre:
            self.etude.etude.titre = titre

        theme = self.theme_combo.currentData()

        if theme:
            self.etude.etude.theme = theme

        reformulation = (
            self.etude.parametres.reformulation
        )

        # P18.11 : plus de prompt/modèle/température
        # écrits (surcharge d'étude des paramètres LLM
        # et prompts abrogée).

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

        resume["longueur_cible_mots"] = [
            self.longueur_min_spin.value(),
            self.longueur_max_spin.value()
        ]

        resume["source_defaut"] = (
            self.source_defaut_combo.currentData()
        )

        from services.bibles import (
            versification_bible,
            version_commune_etude,
        )

        # Ancienne version commune (avant changement).
        ancienne, _mixte_avant = version_commune_etude(
            self.etude
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

        #
        # P18.7e/P18.11 : en v2, les paramètres de
        # traitement vivent dans le TIER de chaque réunion.
        # On propage vers tous les tiers UNIQUEMENT les
        # options d'étude hors LLM conservées par le
        # dialogue (contexte de la reformulation, longueur
        # cible et source du résumé, interdits stylistiques,
        # version Bible) — JAMAIS les paramètres LLM ni
        # les prompts : la surcharge d'étude est abrogée
        # (P18.11c), chaque tier garde ses propres réglages
        # LLM/prompts (éditables via ⚙ Prompts, P18.11e).
        #
        from services.tier_reunion import (
            sauvegarder_tier,
        )

        for nom, tier in self.etude.tiers.items():

            parametres = (
                self.etude.parametres_traitement_de(nom)
            )

            etude_reformulation = (
                self.etude.parametres.reformulation
            )

            parametres.reformulation[
                "fenetre_glissante_tokens"
            ] = etude_reformulation.get(
                "fenetre_glissante_tokens",
                2000,
            )

            parametres.reformulation.setdefault(
                "contexte",
                {},
            ).update(
                etude_reformulation.get("contexte") or {}
            )

            etude_resume = self.etude.parametres.resume

            parametres.resume["longueur_cible_mots"] = (
                etude_resume.get("longueur_cible_mots")
                or [650, 700]
            )

            parametres.resume["source_defaut"] = (
                etude_resume.get(
                    "source_defaut",
                    "reformulations_valides",
                )
            )

            parametres.controle_qualite[
                "interdits_stylistiques"
            ] = list(
                self.etude.parametres.controle_qualite.get(
                    "interdits_stylistiques"
                )
                or []
            )

            #
            # P18.8c : la version de Bible choisie PROPAGE
            # vers le tier de chaque réunion rattachée
            # (ARBITRAGE_P18_7_ECARTS écart 3).
            #
            parametres.bible["version"] = version_bible

            sauvegarder_tier(tier)

        #
        # P18.8c : avertissement de VERSIFICATION au
        # changement (écart = information, jamais de
        # ré-alignement automatique — BIBLE_JND_V2 §4).
        #
        if (
            ancienne
            and version_bible
            and version_bible != ancienne
            and (
                versification_bible(version_bible)
                != versification_bible(ancienne)
            )
        ):
            QMessageBox.warning(
                self,
                "Versifications différentes",
                (
                    "La version retenue change de "
                    "versification ("
                    f"{versification_bible(ancienne)} → "
                    f"{versification_bible(version_bible)}) : "
                    "une même référence peut exister dans "
                    "l'une et pas dans l'autre. "
                    + chr(10) + chr(10)
                    + "C'est une INFORMATION : aucun "
                    "ré-alignement automatique n'est fait ; "
                    "les écarts sont réévalués au prochain "
                    "contrôle qualité (jamais de décision "
                    "automatique — BIBLE_JND_V2)."
                )
            )

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
