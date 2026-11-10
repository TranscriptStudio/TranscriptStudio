# ui/ouvrage_window.py
"""
Page Ouvrage — P19.2/P19.3/P19.4 (feuille de
route v2.1 §P19, maquette validée 2026-10-29) :
l'assemblage, l'édition, la fusion de pensées
et l'export final de l'ouvrage se font ici,
sur le document dérivé P19.1
(services/ouvrage_document.py).

TROIS ZONES :

- à GAUCHE, l'arborescence à la Word (largeur
  réglable) : chapitres (Titre 1, ajoutés
  MANUELLEMENT — l'enchaînement des réunions ne
  suit pas les chapitres), sous-titres,
  paragraphes avec leur réunion source (R1, R2…)
  et les réunions non placées en « Réserves » ;
- au CENTRE, le manuscrit compilé ÉDITABLE :
  titres, sous-titres, séparateurs et
  paragraphes (avec leur provenance) ;
- à DROITE, le rapport : état de la génération,
  signalements « réunion re-reformulée depuis
  la génération », réunions non placées
  (l'analyse de cohérence et la re-vérification
  des versets arrivent avec P20).

Le document ouvrage vit sa PROPRENE vie :
régénérer ÉCRASE tout (avertissement), jamais de
mise à jour automatique incrémentale. L'export
final P18.3 (assemblage des textes validés à la
volée) reste accessible à côté de l'export du
document édité.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import (
    QObject,
    Qt,
    QThread,
    QUrl,
    Signal,
    Slot,
)


class PropositionsSousTitresWorker(QObject):
    """
    P20.2 : passe LLM de proposition de sous-titres
    en arrière-plan (la page reste réactive).
    """

    terminee = Signal(object)
    erreur = Signal(str)

    def __init__(self, service, textes):
        super().__init__()
        self.service = service
        self.textes = textes

    @Slot()
    def run(self):
        try:
            self.terminee.emit(
                self.service.proposer(self.textes)
            )
        except Exception as e:
            self.erreur.emit(str(e))


class LlmWorker(QObject):
    """
    Worker LLM générique (aides à la relecture,
    P20.3/P20.6g) : exécute une fonction sans
    argument en arrière-plan.
    """

    terminee = Signal(object)
    erreur = Signal(str)

    def __init__(self, fonction):
        super().__init__()
        self._fonction = fonction

    @Slot()
    def run(self):
        try:
            self.terminee.emit(self._fonction())
        except Exception as e:
            self.erreur.emit(str(e))

from models.ouvrage import (
    SOURCE_FUSION,
    TYPE_PARAGRAPHE,
    TYPE_SEPARATEUR,
    TYPE_SOUS_TITRE,
    TYPE_TITRE_1,
)
from services.etude_io import EtudeOuverte
from services.help import open_user_manual
from services.ouvrage_document import (
    charger_ouvrage,
    controler_renvois_apres_deplacement,
    deplacer_element,
    defusionner_pensees,
    fusionner_pensees,
    generer_document,
    reformulees_depuis_generation,
    reunions_non_placees,
    sauvegarder_ouvrage,
    supprimer_element,
)
from services.settings import SettingsManager
from ui.fusion_pensees_dialog import (
    FusionPenseesDialog,
)


class OuvrageWindow(QWidget):
    """
    Page Ouvrage d'une étude : arborescence,
    manuscrit éditable, rapport — sur le document
    dérivé P19.1 (ouvrage.json), plus l'export
    final (P18.3).
    """

    def __init__(
        self,
        etude: EtudeOuverte,
        settings=None
    ):
        super().__init__()

        self.etude = etude

        self.settings = (
            settings
            if settings is not None
            else SettingsManager()
        )

        self.document = None
        self.modifie = False

        self.editeurs = {}

        #
        # P20.1 : signalements de renvois orphelins
        # après déplacement (détection locale).
        #
        self._signalements_renvois = []

        #
        # P20.5b : rapport de la dernière
        # re-vérification des versets.
        #
        self._versets_rapport = []

        try:
            self.document = charger_ouvrage(
                self.etude.dossier
            )
        except Exception as e:

            self.document = None

            QMessageBox.warning(
                self,
                "Ouvrage illisible",
                (
                    "Le document ouvrage de cette étude "
                    "n'a pas pu être lu :\\n\\n"
                    + str(e)
                    + "\\n\\n"
                    "Il peut être régénéré depuis les "
                    "textes validés (l'opération "
                    "écrase le document existant)."
                )
            )

        self.build_ui()

        self._reconstruire_zones()

        self._remplir_selecteur_bible_ouvrage()

    def _texte_badge_bible_ouvrage(self) -> str:
        """
        P20.5b : le badge Bible de la page Ouvrage
        affiche la version ouvrage DÈS QU'ELLE est
        choisie (référence d'uniformité).
        """

        if (
            self.document is not None
            and getattr(
                self.document,
                "reference_bible",
                ""
            )
        ):

            from services.bibles import (
                nom_court_bible,
            )

            return (
                "Bible : "
                + nom_court_bible(
                    self.document.reference_bible
                )
            )

        return ""

    def _remplir_selecteur_bible_ouvrage(self):
        """
        P20.5b : sélecteur de la référence
        d'uniformité de l'ouvrage (« Non définie »
        + versions connues), positionné sur la
        valeur persistée dans ouvrage.json.
        """

        from services.bibles import (
            VERSIONS_BIBLE,
            libelle_bible_selecteur,
        )

        self.bible_select.blockSignals(True)

        self.bible_select.clear()

        self.bible_select.addItem(
            "Non définie",
            None
        )

        for identifiant in VERSIONS_BIBLE:

            self.bible_select.addItem(
                libelle_bible_selecteur(identifiant),
                identifiant
            )

        courant = (
            getattr(
                self.document,
                "reference_bible",
                ""
            )
            if self.document is not None
            else ""
        )

        index = self.bible_select.findData(
            courant or None
        )

        self.bible_select.setCurrentIndex(
            index if index >= 0 else 0
        )

        self.bible_select.blockSignals(False)

    def _sur_changement_bible_ouvrage(self, index):
        """
        P20.5b : persiste la référence d'uniformité
        DANS ouvrage.json (couche ouvrage) —
        JAMAIS réécrite vers les tiers des réunions
        (§8bis du CONTRAT_STOCKAGE_REUNIONS).
        """

        if self.document is None:
            return

        version = self.bible_select.currentData() or ""

        if version == getattr(
            self.document,
            "reference_bible",
            ""
        ):
            return

        self.document.reference_bible = version

        sauvegarder_ouvrage(
            self.document,
            self.etude.dossier
        )

        self.badge_bible_label.setText(
            self._texte_badge_bible_ouvrage()
        )

    # ==================================================
    # Construction de l'interface.
    # ==================================================

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        #
        # Ruban (même langage que la page Réunion).
        #
        ruban = QWidget()
        ruban.setObjectName("ruban_ouvrage")

        ruban_layout = QHBoxLayout(ruban)
        ruban_layout.setContentsMargins(0, 0, 0, 0)
        ruban_layout.setSpacing(10)

        self.titre_label = QLabel(
            "Ouvrage — "
            + (
                self.etude.etude.titre
                or "Étude"
            )
        )

        self.titre_label.setStyleSheet(
            "font-size: 18px; font-weight: 600;"
        )

        ruban_layout.addWidget(self.titre_label)

        #
        # P20.5b : référence d'uniformité de
        # l'ouvrage — badge + sélecteur ; persistée
        # dans ouvrage.json, JAMAIS réécrite vers
        # les tiers (§8bis).
        #
        self.badge_bible_label = QLabel(
            self._texte_badge_bible_ouvrage()
        )
        self.badge_bible_label.setStyleSheet(
            "font-size: 12px; color: #1565C0;"
        )

        ruban_layout.addWidget(self.badge_bible_label)

        self.bible_select = QComboBox()
        self.bible_select.setToolTip(
            "Référence d'uniformité de l'ouvrage "
            "(contrôle qualité : re-vérification des "
            "versets) — persistée dans ouvrage.json, "
            "jamais réécrite vers les tiers des "
            "réunions"
        )
        self.bible_select.currentIndexChanged.connect(
            self._sur_changement_bible_ouvrage
        )

        ruban_layout.addWidget(self.bible_select)

        ruban_layout.addStretch()

        self.etude_button = QPushButton(
            "Gestion de l'étude"
        )
        self.etude_button.setToolTip(
            "Ouvrir la page Étude (réunions, "
            "synthèse, paramètres de l'étude)"
        )
        self.etude_button.clicked.connect(
            self.ouvrir_etude
        )

        #
        # P18.10 : icône d'accès au lecteur de Bible
        # intégré (page consultative, pile unique).
        #
        self.bible_button = QPushButton("📖 Bible")
        self.bible_button.setToolTip(
            "Lecteur de Bible intégré (consultation "
            "des versions installées)"
        )
        self.bible_button.clicked.connect(
            self.ouvrir_bible
        )

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
            self.etude_button,
            self.bible_button,
            self.accueil_button,
            self.parametres_button,
            self.aide_button,
        ):
            ruban_layout.addWidget(bouton)

        layout.addWidget(ruban)

        #
        # Barre d'actions de l'ouvrage : générer /
        # régénérer, structure manuelle,
        # sauvegarde, export.
        #
        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.generer_button = QPushButton(
            "⚡ Générer l'ouvrage"
        )
        self.generer_button.setToolTip(
            "Initialise le document ouvrage depuis "
            "les reformulations validées de "
            "l'étude, dans l'ordre d'ouvrage de "
            "chaque réunion (chaque paragraphe "
            "conserve sa provenance)"
        )
        self.generer_button.clicked.connect(
            self.generer_ouvrage
        )

        self.chapitre_button = QPushButton(
            "＋ Chapitre"
        )
        self.chapitre_button.setToolTip(
            "Ajouter un titre de chapitre avant "
            "l'élément sélectionné dans "
            "l'arborescence (ou au début) — "
            "les chapitres sont ajoutés "
            "manuellement"
        )
        self.chapitre_button.clicked.connect(
            lambda: self._ajouter_element(
                TYPE_TITRE_1,
                "Nouveau chapitre",
            )
        )

        self.sous_titre_button = QPushButton(
            "＋ Sous-titre"
        )
        self.sous_titre_button.setToolTip(
            "Ajouter un sous-titre thématique avant "
            "l'élément sélectionné"
        )
        self.sous_titre_button.clicked.connect(
            lambda: self._ajouter_element(
                TYPE_SOUS_TITRE,
                "Nouveau sous-titre",
            )
        )

        self.separateur_button = QPushButton(
            "＋ Séparateur"
        )
        self.separateur_button.setToolTip(
            "Ajouter un séparateur de section avant "
            "l'élément sélectionné"
        )
        self.separateur_button.clicked.connect(
            lambda: self._ajouter_element(
                TYPE_SEPARATEUR,
                "",
            )
        )

        self.fusion_button = QPushButton(
            "Fusionner les pensées…"
        )
        self.fusion_button.setToolTip(
            "Fusionner les DEUX paragraphes "
            "sélectionnés en un seul (P19.4) : le "
            "paragraphe fusionné porte toutes les "
            "provenances ; la fusion est réversible "
            "(dé-fusion)"
        )
        self.fusion_button.clicked.connect(
            self.sur_fusion_pensees
        )

        self.defusion_button = QPushButton(
            "Dé-fusionner"
        )
        self.defusion_button.setToolTip(
            "Restaurer les deux paragraphes d'origine "
            "du paragraphe fusionné sélectionné (le "
            "texte fusionné est conservé dans "
            "l'historique de l'ouvrage)"
        )
        self.defusion_button.clicked.connect(
            self.sur_defusion
        )

        #
        # P20.1 : mobilité inter-blocs des
        # paragraphes — monter / descendre /
        # supprimer l'élément sélectionné (à travers
        # blocs et sections ; la provenance est
        # conservée). Contrôle des renvois orphelins
        # après déplacement (détection locale).
        #
        self.monter_button = QPushButton(
            "↑ Monter"
        )
        self.monter_button.setToolTip(
            "Déplacer l'élément sélectionné d'une "
            "position vers le haut (à travers blocs "
            "et sections ; la provenance des "
            "paragraphes est conservée)"
        )
        self.monter_button.clicked.connect(
            self.monter_selection
        )

        self.descendre_button = QPushButton(
            "↓ Descendre"
        )
        self.descendre_button.setToolTip(
            "Déplacer l'élément sélectionné d'une "
            "position vers le bas"
        )
        self.descendre_button.clicked.connect(
            self.descendre_selection
        )

        self.supprimer_button = QPushButton(
            "✕ Supprimer"
        )
        self.supprimer_button.setToolTip(
            "Supprimer l'élément sélectionné du "
            "document (jamais les textes validés "
            "des réunions)"
        )
        self.supprimer_button.clicked.connect(
            self.supprimer_selection
        )

        #
        # P20.2 : sous-titres proposés par IA pour la
        # section sélectionnée (une passe LLM ;
        # suggestions à valider/éditer, JAMAIS
        # insérées automatiquement).
        #
        self.sous_titres_ia_button = QPushButton(
            "💡 Sous-titres IA…"
        )
        self.sous_titres_ia_button.setToolTip(
            "Proposer 2 à 5 sous-titres sobres pour "
            "structurer la section sélectionnée "
            "(une passe LLM) — suggestions à "
            "valider/éditer, jamais insérées "
            "automatiquement"
        )
        self.sous_titres_ia_button.clicked.connect(
            self.proposer_sous_titres
        )

        self.sauvegarder_button = QPushButton(
            "💾 Sauvegarder"
        )
        self.sauvegarder_button.setToolTip(
            "Écrire le document ouvrage dans "
            "l'étude (ouvrage.json)"
        )
        self.sauvegarder_button.clicked.connect(
            self.sauvegarder_document
        )

        self.exporter_button = QPushButton(
            "📤 Exporter l'ouvrage…"
        )
        self.exporter_button.setToolTip(
            "Assembler les textes validés (résumés "
            "en tête de section, reformulations "
            "dans l'ordre d'ouvrage) et exporter "
            "en document Word ou texte — export "
            "final de l'étude (P18.3)"
        )
        self.exporter_button.clicked.connect(
            self.exporter_ouvrage
        )

        #
        # P20.4 : export DOCX STRUCTURÉ du document
        # édité (styles Titre 1 / sous-titres,
        # métadonnées de réunion en note ou annexe
        # selon réglage).
        #
        self.export_docx_button = QPushButton(
            "📄 Export DOCX structuré…"
        )
        self.export_docx_button.setToolTip(
            "Exporter le document ouvrage édité en "
            "DOCX structuré (Titre 1 / sous-titres ; "
            "métadonnées de réunion en note ou "
            "annexe selon le réglage)"
        )
        self.export_docx_button.clicked.connect(
            self.exporter_document_docx
        )

        #
        # P20.5b : re-vérification des versets
        # bibliques de l'ouvrage contre la référence
        # d'uniformité (version ouvrage choisie),
        # écarts signalés comme informations.
        #
        self.reverifier_versets_button = QPushButton(
            "🔎 Re-vérifier les versets"
        )
        self.reverifier_versets_button.setToolTip(
            "Re-vérifier les références bibliques de "
            "l'ouvrage contre la version retenue "
            "(référence d'uniformité de l'ouvrage si "
            "choisie, sinon version de l'étude) — "
            "écarts de versification = information"
        )
        self.reverifier_versets_button.clicked.connect(
            self.reverifier_versets
        )

        for bouton in (
            self.generer_button,
            self.chapitre_button,
            self.sous_titre_button,
            self.separateur_button,
            self.fusion_button,
            self.defusion_button,
            self.monter_button,
            self.descendre_button,
            self.supprimer_button,
            self.sous_titres_ia_button,
            self.sauvegarder_button,
            self.exporter_button,
            self.export_docx_button,
            self.reverifier_versets_button,
        ):
            actions.addWidget(bouton)

        actions.addStretch()

        layout.addLayout(actions)

        #
        # Trois zones (maquette validée) :
        # arborescence | manuscrit | rapport.
        #
        split = QSplitter(
            Qt.Orientation.Horizontal
        )

        split.addWidget(
            self._construire_zone_arborescence()
        )

        split.addWidget(
            self._construire_zone_manuscrit()
        )

        split.addWidget(
            self._construire_zone_rapport()
        )

        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)

        split.setSizes([260, 700, 260])

        layout.addWidget(split, stretch=1)

        self._maj_outils()

        #
        # P18.9e : fond de page des maquettes, ruban
        # et labels à la teinte EXACTE du fond de
        # page (correctif transverse).
        #
        self._appliquer_fond_page()

    def _appliquer_fond_page(self):
        """
        P18.9e : fond de page des maquettes dans les
        DEUX thèmes, ruban et labels transparents —
        teinte EXACTE du fond de page (helper partagé
        ``feuille_fond_page``).
        """

        from services.theme_manager import (
            est_sombre,
            feuille_fond_page,
        )

        self.setAttribute(
            Qt.WidgetAttribute
            .WA_StyledBackground,
            True
        )

        self.setStyleSheet(
            feuille_fond_page(
                "OuvrageWindow",
                est_sombre(self)
            )
        )

    def sur_changement_theme(self):
        """
        Broadcast de ThemeManager : réapplique le
        fond de page (P18.9e).
        """

        self._appliquer_fond_page()

    def _construire_zone_arborescence(self) -> QWidget:
        """
        Zone GAUCHE : arborescence à la Word —
        chapitres, sous-titres, paragraphes avec
        leur réunion source, et les réunions non
        placées en « Réserves ».
        """

        zone = QWidget()

        colonne = QVBoxLayout(zone)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        entete = QLabel("Structure")
        entete.setStyleSheet(
            "font-weight: 600;"
        )

        colonne.addWidget(entete)

        self.arbre = QTreeWidget()
        self.arbre.setHeaderHidden(True)
        self.arbre.setAnimated(True)

        # Sélection multiple : la fusion de pensées
        # (P19.4) porte sur DEUX paragraphes choisis
        # dans l'arborescence.
        self.arbre.setSelectionMode(
            QTreeWidget.SelectionMode
            .ExtendedSelection
        )

        self.arbre.itemClicked.connect(
            self._sur_clic_arbre
        )

        self.arbre.itemSelectionChanged.connect(
            self._maj_outils
        )

        colonne.addWidget(self.arbre, stretch=1)

        return zone

    def _construire_zone_manuscrit(self) -> QWidget:
        """
        Zone CENTRE : le manuscrit compilé,
        ÉDITABLE — titres, sous-titres,
        séparateurs, paragraphes avec leur
        provenance.
        """

        zone = QWidget()

        colonne = QVBoxLayout(zone)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        entete = QLabel("Manuscrit")
        entete.setStyleSheet(
            "font-weight: 600;"
        )

        colonne.addWidget(entete)

        self.manuscrit_defile = QScrollArea()
        self.manuscrit_defile.setWidgetResizable(
            True
        )

        self.manuscrit_defile.setFrameShape(
            QScrollArea.Shape.NoFrame
        )

        self.manuscrit_conteneur = QWidget()

        self.manuscrit_layout = QVBoxLayout(
            self.manuscrit_conteneur
        )

        self.manuscrit_layout.setContentsMargins(
            6, 6, 6, 6
        )

        self.manuscrit_layout.setSpacing(10)

        self.manuscrit_layout.addStretch()

        self.manuscrit_defile.setWidget(
            self.manuscrit_conteneur
        )

        colonne.addWidget(
            self.manuscrit_defile,
            stretch=1
        )

        return zone

    def _construire_zone_rapport(self) -> QWidget:
        """
        Zone DROITE : rapport — état de la
        génération, signalements de divergence,
        réunions non placées, renvois orphelins
        (P20.1) — PLUS les aides à la relecture
        (P20.3, emplacement UNIQUE page Ouvrage :
        emphases, expressions récurrentes,
        cohérence par section, pensées
        redondantes P20.6g) avec occurrences
        cliquables et filtres.
        """

        zone = QWidget()

        colonne = QVBoxLayout(zone)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        entete = QLabel("Rapport")
        entete.setStyleSheet(
            "font-weight: 600;"
        )

        colonne.addWidget(entete)

        self.rapport_zone = QPlainTextEdit()
        self.rapport_zone.setReadOnly(True)

        colonne.addWidget(
            self.rapport_zone,
            stretch=1
        )

        #
        # P20.3 : aides à la relecture (page Ouvrage
        # seule — amendement du 09/11).
        #
        entete_relecture = QLabel(
            "Aides à la relecture (signalement "
            "uniquement, jamais de réécriture)"
        )
        entete_relecture.setStyleSheet(
            "font-weight: 600;"
        )

        colonne.addWidget(entete_relecture)

        ligne_aides = QHBoxLayout()

        self.emphases_button = QPushButton(
            "Emphases…"
        )
        self.emphases_button.setToolTip(
            "Récurrence d'emphase (intensifs) sur "
            "l'ouvrage — détection locale, sans LLM"
        )
        self.emphases_button.clicked.connect(
            self.afficher_emphases
        )

        self.expressions_button = QPushButton(
            "Récurrences…"
        )
        self.expressions_button.setToolTip(
            "Expressions récurrentes de l'ouvrage "
            "(n-grammes, familles) — local, sans "
            "LLM ; passe LLM optionnelle sur les "
            "familles"
        )
        self.expressions_button.clicked.connect(
            self.afficher_expressions
        )

        self.coherence_button = QPushButton(
            "Cohérence section… (IA)"
        )
        self.coherence_button.setToolTip(
            "Incohérences et redondances de la "
            "section sélectionnée — une passe LLM "
            "à la demande ; signalement uniquement"
        )
        self.coherence_button.clicked.connect(
            self.analyser_coherence
        )

        self.redondances_button = QPushButton(
            "Pensées redondantes…"
        )
        self.redondances_button.setToolTip(
            "P20.6g : présélection locale (sans "
            "LLM) des pensées redondantes de la "
            "synthèse, reliées aux paragraphes de "
            "l'ouvrage ; confirmation LLM à la "
            "demande"
        )
        self.redondances_button.clicked.connect(
            self.detecter_pensees_redondantes
        )

        for bouton in (
            self.emphases_button,
            self.expressions_button,
            self.coherence_button,
            self.redondances_button,
        ):
            ligne_aides.addWidget(bouton)

        colonne.addLayout(ligne_aides)

        # Filtres (réunion, chapitre, intervenant).
        ligne_filtres = QHBoxLayout()

        self.filtre_reunion = QComboBox()
        self.filtre_reunion.addItem(
            "Toutes les réunions",
            None
        )

        self.filtre_chapitre = QComboBox()
        self.filtre_chapitre.addItem(
            "Tous les chapitres",
            None
        )

        self.filtre_locuteur = QComboBox()
        self.filtre_locuteur.addItem(
            "Tous les intervenants",
            None
        )

        for combo in (
            self.filtre_reunion,
            self.filtre_chapitre,
            self.filtre_locuteur,
        ):
            combo.currentIndexChanged.connect(
                self._reappliquer_filtres
            )
            ligne_filtres.addWidget(combo)

        colonne.addLayout(ligne_filtres)

        # Résultats : occurrences cliquables (liens
        # vers les paragraphes du manuscrit).
        self.resultats_arbre = QTreeWidget()
        self.resultats_arbre.setHeaderHidden(True)
        self.resultats_arbre.itemClicked.connect(
            self._sur_clic_resultat
        )

        colonne.addWidget(
            self.resultats_arbre,
            stretch=1
        )

        # Dernier jeu de résultats (pour les filtres).
        self._dernier_resultat = None

        return zone

    # ==================================================
    # Reconstruction des zones depuis le document.
    # ==================================================

    def _reconstruire_zones(self):
        """
        Reconstruit l'arborescence, le manuscrit
        et le rapport depuis le document courant.
        """

        self._reconstruire_manuscrit()
        self._reconstruire_arborescence()
        self._reconstruire_rapport()
        self._maj_outils()

    def _reconstruire_manuscrit(self):
        """
        Le manuscrit : un éditeur par élément —
        titres et sous-titres éditables en place,
        séparateur discret, paragraphe éditable
        avec sa provenance dessous.
        """

        while self.manuscrit_layout.count() > 1:

            item = self.manuscrit_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self.editeurs = {}

        if self.document is None:
            return

        for element in self.document.elements:

            if (
                element.type == TYPE_TITRE_1
                or element.type
                == TYPE_SOUS_TITRE
            ):

                editeur = self._editeur_titre(
                    element
                )

            elif element.type == TYPE_SEPARATEUR:

                editeur = self._editeur_separateur(
                    element
                )

            else:

                editeur = self._editeur_paragraphe(
                    element
                )

            self.manuscrit_layout.addWidget(
                editeur
            )

            self.editeurs[element.id] = editeur

        self.manuscrit_layout.addStretch()

    def _editeur_titre(self, element) -> QWidget:
        """
        Titre (chapitre) ou sous-titre : édité en
        place — chapitre en 16 px gras,
        sous-titre en 13 px.
        """

        editeur = QLineEdit(element.texte)

        if element.type == TYPE_TITRE_1:
            editeur.setStyleSheet(
                "font-size: 16px; font-weight: 600;"
                "border: none;"
                "background: transparent;"
            )
        else:
            editeur.setStyleSheet(
                "font-size: 13px; font-weight: 600;"
                "border: none;"
                "background: transparent;"
            )

        editeur.textChanged.connect(
            lambda texte, e=element: (
                self._sur_texte_element(e, texte)
            )
        )

        editeur.element_id = element.id

        return editeur

    def _editeur_separateur(
        self,
        element
    ) -> QWidget:
        """
        Séparateur de section : filet discret, non
        éditable.
        """

        filet = QFrame()
        filet.setFrameShape(
            QFrame.Shape.HLine
        )

        filet.setStyleSheet(
            "color: #8a8b92;"
        )

        filet.element_id = element.id

        return filet

    def _editeur_paragraphe(self, element) -> QWidget:
        """
        Paragraphe : texte éditable, provenance en
        dessous (réunion source, date, FID —
        métadonnées NON structurelles).
        """

        bloc = QWidget()

        colonne = QVBoxLayout(bloc)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(2)

        editeur = QTextEdit(element.texte)
        editeur.setAcceptRichText(False)

        editeur.setTabChangesFocus(True)

        editeur.textChanged.connect(
            lambda e=element,
            t=editeur: (
                self._sur_texte_element(
                    e,
                    t.toPlainText()
                )
            )
        )

        editeur.textChanged.connect(
            lambda t=editeur: (
                self._ajuster_hauteur_editeur(t)
            )
        )

        colonne.addWidget(editeur)

        provenances = []

        for p in element.provenances:

            morceau = (
                f"R{p.numero_reunion}"
                if p.numero_reunion
                else p.reunion
            )

            if p.locuteurs:
                morceau += f" · {p.locuteurs}"

            if p.date_reunion:
                morceau += f" · {p.date_reunion}"

            if p.fid:
                morceau += f" · bloc {p.fid}"

            provenances.append(morceau)

        provenance_label = QLabel(
            (
                "Fusion de pensées — "
                if element.source == SOURCE_FUSION
                else ""
            )
            + " — ".join(provenances)
        )

        # P19.4-bis : traçabilité du prompt de
        # l'assistance éventuelle (hash court).
        if element.source == SOURCE_FUSION and (
            element.fusion
        ):

            stats = (
                element.fusion.get("stats") or {}
            )

            if stats.get("prompt_hash"):
                provenance_label.setText(
                    provenance_label.text()
                    + f" · prompt {stats['prompt_hash']}"
                )

        provenance_label.setStyleSheet(
            "color: #8a8b92; font-size: 11px;"
        )

        colonne.addWidget(provenance_label)

        bloc.element_id = element.id

        return bloc

    def _ajuster_hauteur_editeur(self, editeur):
        """
        Hauteur du paragraphe = son contenu (pas de
        défilement interne).
        """

        hauteur = int(
            editeur.document()
            .size()
            .height()
        ) + 12

        editeur.setFixedHeight(hauteur)

    # ==================================================
    # Arborescence.
    # ==================================================

    def _reconstruire_arborescence(self):
        """
        L'arborescence : chapitres avec leurs
        sous-titres et paragraphes (réunion source
        R1, R2…), et les paragraphes non placés
        sous « Réserves ».
        """

        self.arbre.clear()

        if self.document is None:
            return

        chapitre_courant = None
        sous_titre_courant = None

        for element in self.document.elements:

            if element.type == TYPE_TITRE_1:

                chapitre_courant = (
                    QTreeWidgetItem(
                        [element.texte or "Chapitre"]
                    )
                )

                self._gras(chapitre_courant)

                chapitre_courant.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    element.id,
                )

                self.arbre.addTopLevelItem(
                    chapitre_courant
                )

                sous_titre_courant = None

                continue

            if element.type == TYPE_SOUS_TITRE:

                parent = (
                    sous_titre_courant
                    or chapitre_courant
                )

                if parent is None:
                    continue

                sous_titre_courant = (
                    QTreeWidgetItem(
                        [element.texte or "Sous-titre"]
                    )
                )

                sous_titre_courant.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    element.id,
                )

                parent.addChild(
                    sous_titre_courant
                )

                continue

            if element.type != TYPE_PARAGRAPHE:
                continue

            libelle = (
                self._libelle_arbre_paragraphe(
                    element
                )
            )

            item = QTreeWidgetItem([libelle])

            item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                element.id,
            )

            parent = (
                sous_titre_courant
                or chapitre_courant
            )

            if parent is not None:
                parent.addChild(item)

        #
        # Réserves : les paragraphes non placés
        # (avant le premier chapitre).
        #
        reserves = (
            self.document.paragraphes_reserves()
        )

        if reserves:

            noeud = QTreeWidgetItem(
                ["Réserves"]
            )

            self._gras(noeud)

            for element in reserves:

                libelle = (
                    self._libelle_arbre_paragraphe(
                        element
                    )
                )

                item = QTreeWidgetItem([libelle])

                item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    element.id,
                )

                noeud.addChild(item)

            self.arbre.addTopLevelItem(noeud)

        self.arbre.expandAll()

    @staticmethod
    def _libelle_arbre_paragraphe(element) -> str:
        """
        Libellé d'un paragraphe dans l'arborescence :
        réunion(s) source puis extrait du texte —
        un paragraphe FUSIONNÉ (P19.4) montre
        toutes ses réunions (R1/R2).
        """

        extrait = (
            (element.texte or "")[:60].strip()
            or "Paragraphe"
        )

        numeros = []

        for p in element.provenances:

            numero = (
                f"R{p.numero_reunion}"
                if p.numero_reunion
                else (p.reunion or "?")
            )

            if numero not in numeros:
                numeros.append(numero)

        if not numeros:
            return extrait

        return "/".join(numeros) + " — " + extrait

    @staticmethod
    def _gras(item):
        """
        Met un élément d'arborescence en gras
        (chapitre, Réserves).
        """

        from PySide6.QtGui import QFont

        police = item.font(0)
        police.setBold(True)
        item.setFont(0, police)

    def _sur_clic_arbre(self, item):
        """
        Navigation par structure : le clic amène le
        manuscrit à l'élément correspondant.
        """

        identifiant = item.data(
            0,
            Qt.ItemDataRole.UserRole
        )

        if not identifiant:
            return

        editeur = self.editeurs.get(identifiant)

        if editeur is not None:

            self.manuscrit_defile.ensureWidgetVisible(
                editeur
            )

            editeur.setFocus()

    # ==================================================
    # Rapport.
    # ==================================================

    def _reconstruire_rapport(self):
        """
        Le rapport : état de la génération,
        signalements « réunion re-reformulée depuis
        la génération », réunions non placées.
        """

        if self.document is None:

            self.rapport_zone.setPlainText(
                "Aucun ouvrage généré.\n\n"
                "« Générer l'ouvrage » initialise le "
                "document depuis les reformulations "
                "validées de l'étude."
            )

            return

        lignes = []

        generation = (
            self.document.generation or {}
        )

        horodatage = generation.get(
            "horodatage"
        )

        paragraphes = (
            len(self.document.paragraphes())
        )

        chapitres = [
            e for e in self.document.elements
            if e.type == TYPE_TITRE_1
        ]

        lignes.append(
            "Ouvrage généré le "
            + (horodatage or "?")
        )

        lignes.append(
            f"{paragraphes} paragraphe(s) · "
            f"{len(chapitres)} chapitre(s)"
        )

        #
        # Fusions de pensées (P19.4) : paragraphes
        # fusionnés du corps, fusions dé-faites
        # conservées dans l'historique.
        #
        fusions = [
            p for p in self.document.paragraphes()
            if p.source == SOURCE_FUSION
        ]

        if fusions:

            lignes.append("")

            lignes.append(
                "Fusions de pensées : "
                f"{len(fusions)} paragraphe(s) "
                "fusionné(s) (dé-fusion possible)"
            )

        if self.document.historique:

            lignes.append(
                "Historique : "
                f"{len(self.document.historique)} "
                "fusion(s) dé-fusionnée(s) conservée(s)"
            )

        #
        # Signalements de divergence (le document
        # dérivé n'est JAMAIS mis à jour
        # automatiquement).
        #
        divergences = (
            reformulees_depuis_generation(
                self.document,
                self.etude
            )
        )

        if divergences:

            lignes.append("")
            lignes.append(
                "Re-reformulé depuis la génération :"
            )

            for d in divergences:

                lignes.append(
                    f"· R{d['reunion'][:24]} — "
                    f"bloc {d['fid']} "
                    f"(v{d['version_courante']} > "
                    f"v{d['version_generation']})"
                )

        non_placees = reunions_non_placees(
            self.document,
            self.etude
        )

        if non_placees:

            lignes.append("")
            lignes.append("Non placées (Réserves) :")

            for nom in non_placees:
                lignes.append("· " + nom)

        #
        # P20.1 : renvois orphelins après déplacement
        # (signalement local, jamais de modification).
        #
        if self._signalements_renvois:

            lignes.append("")
            lignes.append(
                "Renvois possiblement orphelins après "
                "déplacement (signalement local) :"
            )

            for s in self._signalements_renvois:

                lignes.append(
                    f"· paragraphe {s['id']} : "
                    + ", ".join(
                        f"« {r} »" for r in s["renvois"]
                    )
                )

        #
        # P20.5b : rapport de la dernière
        # re-vérification des versets.
        #
        if self._versets_rapport:

            lignes.append("")
            lignes.extend(self._versets_rapport)

        self.rapport_zone.setPlainText(
            "\n".join(lignes)
        )

        #
        # P20.3 : filtres des aides à la relecture
        # (réunion, chapitre, intervenant).
        #
        self._remplir_filtres()

    # ==================================================
    # Actions.
    # ==================================================

    def _maj_outils(self):
        """
        Active les outils selon la présence du
        document (générer vs régénérer, structure,
        sauvegarde) et l'état modifié.
        """

        avec_document = self.document is not None

        self.generer_button.setText(
            "⟳ Régénérer…"
            if avec_document
            else "⚡ Générer l'ouvrage"
        )

        for bouton in (
            self.chapitre_button,
            self.sous_titre_button,
            self.separateur_button,
        ):
            bouton.setEnabled(avec_document)

        self.sauvegarder_button.setEnabled(
            avec_document and self.modifie
        )

        #
        # Fusion de pensées (P19.4) : deux
        # paragraphes sélectionnés ; dé-fusion :
        # un paragraphe issu d'une fusion.
        #
        paragraphes = (
            self._paragraphes_selectionnes()
            if avec_document
            else []
        )

        self.fusion_button.setEnabled(
            len(paragraphes) == 2
        )

        self.defusion_button.setEnabled(
            len(paragraphes) == 1
            and paragraphes[0].source
            == SOURCE_FUSION
        )

        #
        # P20.1 : mobilité — un élément sélectionné.
        #
        ids = self._ids_selection()

        self.monter_button.setEnabled(
            avec_document and len(ids) == 1
        )

        self.descendre_button.setEnabled(
            avec_document and len(ids) == 1
        )

        self.supprimer_button.setEnabled(
            avec_document and len(ids) == 1
        )

        #
        # P20.2 : proposition de sous-titres pour la
        # section de l'élément sélectionné.
        #
        self.sous_titres_ia_button.setEnabled(
            avec_document and len(ids) == 1
        )

    def generer_ouvrage(self):
        """
        P19.3 : génère — ou RÉGÉNÈRE, opération qui
        ÉCRASE le document existant (avertissement
        explicite ; jamais de mise à jour
        incrémentale).
        """

        if self.document is not None:

            reponse = QMessageBox.warning(
                self,
                "Régénérer l'ouvrage ?",
                (
                    "Régénérer ÉCRASE le document "
                    "ouvrage actuel : chapitres, "
                    "sous-titres, séparateurs et "
                    "éditions disparaissent — "
                    "Y COMPRIS les FUSIONS de "
                    "pensées (et l'historique) — "
                    "seuls les textes validés de "
                    "l'étude sont réimportés.\n\n"
                    "Continuer ?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox
                    .StandardButton.No
                ),
                (
                    QMessageBox
                    .StandardButton.No
                ),
            )

            if reponse != (
                QMessageBox.StandardButton.Yes
            ):
                return

        self.document = generer_document(
            self.etude
        )

        sauvegarder_ouvrage(
            self.document,
            self.etude.dossier
        )

        self.modifie = False

        self._reconstruire_zones()

    def _ajouter_element(self, type_element, texte):
        """
        Ajoute un élément de structure AVANT
        l'élément sélectionné dans l'arborescence
        (au début si rien n'est sélectionné) —
        les chapitres sont ajoutés MANUELLEMENT.
        """

        from models.ouvrage import (
            ElementOuvrage,
        )

        prefixes = {
            TYPE_TITRE_1: "t1",
            TYPE_SOUS_TITRE: "st",
            TYPE_SEPARATEUR: "sep",
        }

        element = ElementOuvrage(
            id=self.document.nouvel_id(
                prefixes[type_element]
            ),
            type=type_element,
            texte=texte,
        )

        position = self._position_selection()

        self.document.elements.insert(
            position,
            element
        )

        self.modifie = True

        self._reconstruire_zones()

    def _position_selection(self) -> int:
        """
        Index d'insertion : avant l'élément
        sélectionné dans l'arborescence (son id →
        position dans le document), au début si
        rien n'est sélectionné.
        """

        item = self.arbre.currentItem()

        if item is None:
            return 0

        identifiant = item.data(
            0,
            Qt.ItemDataRole.UserRole
        )

        if not identifiant:
            return 0

        for index, element in enumerate(
            self.document.elements
        ):

            if element.id == identifiant:
                return index

        return 0

    def _ids_selection(self) -> list:
        """
        Identifiants des éléments sélectionnés dans
        l'arborescence (dédupliqués, ordre de
        sélection) — la fusion (P19.4) porte sur
        les PARAGRAPHES sélectionnés.
        """

        ids = []

        for item in (
            self.arbre.selectedItems() or []
        ):

            identifiant = item.data(
                0,
                Qt.ItemDataRole.UserRole
            )

            if identifiant and (
                identifiant not in ids
            ):
                ids.append(identifiant)

        return ids

    def _paragraphes_selectionnes(self) -> list:
        """
        Les PARAGRAPHES du document actuellement
        sélectionnés dans l'arborescence, dans
        l'ORDRE DU DOCUMENT.
        """

        if self.document is None:
            return []

        paragraphes = []

        for identifiant in self._ids_selection():

            element = self.document.element(
                identifiant
            )

            if (
                element is not None
                and element.type == TYPE_PARAGRAPHE
                and element not in paragraphes
            ):
                paragraphes.append(element)

        paragraphes.sort(
            key=self.document.elements.index
        )

        return paragraphes

    def sur_fusion_pensees(self):
        """
        **Fusion de pensées** (P19.4) : deux
        paragraphes sélectionnés deviennent UN
        SEUL paragraphe portant les provenances
        multiples — dialogue côte à côte, fusion
        manuelle ou assistance IA ; « Annuler » ne
        touche à rien (l'assistance reste une
        proposition, jamais appliquée sans
        validation explicite).

        Opération de COMPOSITION DE L'OUVRAGE,
        uniquement : ni les textes validés ni le
        registre de l'étude ne bougent.
        """

        paragraphes = (
            self._paragraphes_selectionnes()
        )

        if len(paragraphes) != 2:
            return

        from services.traitements.fusion import (
            ServiceFusion,
        )

        try:
            service = ServiceFusion(self.etude)
        except Exception:
            service = None

        dialogue = FusionPenseesDialog(
            self,
            paragraphes[0],
            paragraphes[1],
            service=service,
        )

        if (
            dialogue.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        try:

            fusionner_pensees(
                self.document,
                paragraphes[0].id,
                paragraphes[1].id,
                dialogue.texte_fusionne(),
                stats=dialogue.stats(),
            )

        except Exception as e:

            QMessageBox.warning(
                self,
                "Fusion impossible",
                str(e)
            )

            return

        self.modifie = True

        self._reconstruire_zones()

    def sur_defusion(self):
        """
        **Dé-fusion** (P19.4) : le paragraphe fusionné
        sélectionné disparaît du corps du document ;
        chacun des deux paragraphes d'origine
        REPREND son texte — le texte fusionné est
        conservé dans l'historique de l'ouvrage.
        """

        paragraphes = (
            self._paragraphes_selectionnes()
        )

        if len(paragraphes) != 1:
            return

        fusionne = paragraphes[0]

        reponse = QMessageBox.question(
            self,
            "Dé-fusionner ?",
            (
                "Le paragraphe fusionné sera remplacé "
                "par ses deux paragraphes d'origine "
                "(chacun reprend son texte). Le texte "
                "fusionné est conservé dans "
                "l'historique de l'ouvrage.\n\n"
                "Continuer ?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            (
                QMessageBox.StandardButton.No
            ),
        )

        if reponse != (
            QMessageBox.StandardButton.Yes
        ):
            return

        try:

            defusionner_pensees(
                self.document,
                fusionne.id
            )

        except Exception as e:

            QMessageBox.warning(
                self,
                "Dé-fusion impossible",
                str(e)
            )

            return

        self.modifie = True

        self._reconstruire_zones()

    # ==================================================
    # P20.1 — mobilité inter-blocs des paragraphes.
    # ==================================================

    def _element_selectionne(self):
        """
        L'élément du document sélectionné dans
        l'arborescence (None si aucun / multiple).
        """

        if self.document is None:
            return None

        ids = self._ids_selection()

        if len(ids) != 1:
            return None

        return self.document.element(ids[0])

    def _deplacer_selection(self, offset: int):
        """
        Déplace l'élément sélectionné d'``offset``
        positions dans le document (à travers blocs
        et sections ; provenance conservée), puis
        contrôle les renvois orphelins (détection
        locale — signalement uniquement).
        """

        element = self._element_selectionne()

        if element is None:
            return

        ancienne_position = (
            self.document.elements.index(element)
        )

        precedent_avant_id = (
            self.document.elements[
                ancienne_position - 1
            ].id
            if ancienne_position > 0
            else None
        )

        nouvelle_position = max(
            0,
            min(
                ancienne_position + offset,
                len(self.document.elements) - 1
            )
        )

        if nouvelle_position == ancienne_position:
            return

        try:

            deplacer_element(
                self.document,
                element.id,
                nouvelle_position
            )

        except Exception as e:

            QMessageBox.warning(
                self,
                "Déplacement impossible",
                str(e)
            )
            return

        self.modifie = True

        #
        # Contrôle des renvois orphelins après
        # déplacement (P20.1, détection locale) :
        # signalements affichés dans le rapport,
        # jamais de modification automatique.
        #
        self._signalements_renvois = (
            controler_renvois_apres_deplacement(
                self.document,
                element.id,
                ancienne_position,
                precedent_avant_id=precedent_avant_id
            )
        )

        self._reconstruire_zones()

    def monter_selection(self):
        self._deplacer_selection(-1)

    def descendre_selection(self):
        self._deplacer_selection(1)

    def supprimer_selection(self):
        """
        Suppression d'un élément du document (P20.1)
        — le document dérivé seul est touché, jamais
        les textes validés des réunions (§8bis).
        """

        element = self._element_selectionne()

        if element is None:
            return

        reponse = QMessageBox.question(
            self,
            "Supprimer l'élément ?",
            (
                "Supprimer cet élément du document "
                "ouvrage ?\n\nLes textes validés des "
                "réunions ne sont pas touchés."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if reponse != QMessageBox.StandardButton.Yes:
            return

        try:

            supprimer_element(
                self.document,
                element.id
            )

        except Exception as e:

            QMessageBox.warning(
                self,
                "Suppression impossible",
                str(e)
            )
            return

        self.modifie = True

        self._reconstruire_zones()

    # ==================================================
    # P20.2 — sous-titres proposés par IA.
    # ==================================================

    def _section_selection(self):
        """
        La section de l'élément sélectionné :
        ``(titre_1 ou None, [paragraphes])`` — du
        titre de chapitre précédant (ou début du
        document) jusqu'au titre de chapitre suivant.
        """

        if self.document is None:
            return None, []

        ids = self._ids_selection()

        if len(ids) != 1:
            return None, []

        element = self.document.element(ids[0])

        if element is None:
            return None, []

        index = self.document.elements.index(element)

        # Titre de chapitre de la section.
        titre = None

        for i in range(index, -1, -1):

            if (
                self.document.elements[i].type
                == TYPE_TITRE_1
            ):
                titre = self.document.elements[i]
                break

        debut = (
            self.document.elements.index(titre) + 1
            if titre is not None
            else 0
        )

        fin = len(self.document.elements)

        for i in range(debut, len(self.document.elements)):

            if (
                self.document.elements[i].type
                == TYPE_TITRE_1
            ):
                fin = i
                break

        paragraphes = [
            e for e in self.document.elements[
                debut:fin
            ]
            if e.type == TYPE_PARAGRAPHE
        ]

        return titre, paragraphes

    def proposer_sous_titres(self):
        """
        P20.2 : UNE passe LLM sur la section
        sélectionnée ; les suggestions sont soumises
        à validation/édition (dialogue) — JAMAIS
        insérées automatiquement.
        """

        titre, paragraphes = self._section_selection()

        if not paragraphes:

            QMessageBox.information(
                self,
                "Section vide",
                "La section sélectionnée ne comporte "
                "aucun paragraphe à structurer."
            )
            return

        from services.traitements.sous_titres import (
            ServiceSousTitres,
        )

        service = ServiceSousTitres(self.etude)

        textes = [p.texte for p in paragraphes]

        if getattr(self, "_sous_titres_thread", None):
            return

        #
        # Fenêtre de chargement (règle 2026-11-07) :
        # un appel LLM — temps écoulé affiché.
        #
        from ui.fenetre_chargement_llm import (
            FenetreChargementLLM,
        )

        self._fenetre_chargement = FenetreChargementLLM(
            "Proposition de sous-titres…",
            parent=self,
            message=(
                "Appel LLM en cours (sous-titres IA)…"
            ),
        )

        self._fenetre_chargement.set_indeterminee()
        self._fenetre_chargement.show()

        self._sous_titres_thread = QThread(self)

        self._sous_titres_worker = (
            PropositionsSousTitresWorker(
                service,
                textes
            )
        )

        self._sous_titres_worker.moveToThread(
            self._sous_titres_thread
        )

        self._sous_titres_thread.started.connect(
            self._sous_titres_worker.run
        )

        self._sous_titres_worker.terminee.connect(
            self._sur_sous_titres_proposes
        )

        self._sous_titres_worker.erreur.connect(
            self._sur_sous_titres_erreur
        )

        self._sous_titres_thread.start()

    def _sur_sous_titres_proposes(self, resultat):

        if getattr(
            self,
            "_fenetre_chargement",
            None
        ) is not None:
            self._fenetre_chargement.fermer()
            self._fenetre_chargement = None

        self._sous_titres_thread.quit()
        self._sous_titres_thread = None
        self._sous_titres_worker = None

        suggestions, stats = resultat

        if not suggestions:

            QMessageBox.information(
                self,
                "Aucune proposition",
                "Le modèle n'a proposé aucun sous-titre."
            )
            return

        titre, _paragraphes = self._section_selection()

        from ui.sous_titres_dialog import (
            SousTitresDialog,
        )

        dialogue = SousTitresDialog(
            suggestions,
            titre_section=(
                titre.texte if titre is not None else ""
            ),
            parent=self,
        )

        if (
            dialogue.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        retenues = dialogue.suggestions_retenues()

        if not retenues:
            return

        self._inserer_sous_titres(retenues)

        QMessageBox.information(
            self,
            "Sous-titres insérés",
            (
                f"{len(retenues)} sous-titre(s) "
                "inséré(s) dans la section (coût réel : "
                f"{stats.get('cout_estime', 0.0):.4f} $)."
            )
        )

    def _sur_sous_titres_erreur(self, message):

        if getattr(
            self,
            "_fenetre_chargement",
            None
        ) is not None:
            self._fenetre_chargement.fermer()
            self._fenetre_chargement = None

        self._sous_titres_thread.quit()
        self._sous_titres_thread = None
        self._sous_titres_worker = None

        QMessageBox.warning(
            self,
            "Sous-titres non proposés",
            message
        )

    def _inserer_sous_titres(self, retenues: list):
        """
        Insère les sous-titres VALIDÉS (après le
        dialogue) en tête de la section sélectionnée
        — jamais automatiquement.
        """

        from models.ouvrage import (
            ElementOuvrage,
        )

        titre, _paragraphes = self._section_selection()

        if titre is not None:
            position = (
                self.document.elements.index(titre) + 1
            )
        else:
            position = 0

        for offset, texte in enumerate(retenues):

            element = ElementOuvrage(
                id=self.document.nouvel_id("st"),
                type=TYPE_SOUS_TITRE,
                texte=texte,
            )

            self.document.elements.insert(
                position + offset,
                element
            )

        self.modifie = True

        self._reconstruire_zones()

    # ==================================================
    # P20.3 / P20.6g — aides à la relecture (page
    # Ouvrage seule). Signalement uniquement.
    # ==================================================

    def _lancer_llm(self, fonction, on_ok, on_err):
        """
        Lance un appel LLM en arrière-plan (fenêtre
        de chargement, règle 2026-11-07) avec
        ``fonction`` (appelable sans argument).
        """

        if getattr(self, "_relecture_thread", None):
            return

        from ui.fenetre_chargement_llm import (
            FenetreChargementLLM,
        )

        self._fenetre_chargement = FenetreChargementLLM(
            "Appel LLM en cours…",
            parent=self,
            message="Appel LLM en cours (relecture)…",
        )

        self._fenetre_chargement.set_indeterminee()
        self._fenetre_chargement.show()

        self._relecture_thread = QThread(self)

        self._relecture_worker = LlmWorker(fonction)

        self._relecture_worker.moveToThread(
            self._relecture_thread
        )

        self._relecture_thread.started.connect(
            self._relecture_worker.run
        )

        self._relecture_worker.terminee.connect(on_ok)
        self._relecture_worker.erreur.connect(on_err)

        self._relecture_thread.start()

    def _arreter_llm(self):

        if getattr(
            self,
            "_fenetre_chargement",
            None
        ) is not None:
            self._fenetre_chargement.fermer()
            self._fenetre_chargement = None

        if getattr(self, "_relecture_thread", None):
            self._relecture_thread.quit()

        self._relecture_thread = None
        self._relecture_worker = None

    def _remplir_filtres(self):

        if self.document is None:
            return

        reunions = set()
        locuteurs = set()

        for p in self.document.paragraphes():

            for prov in p.provenances:

                if prov.reunion:
                    reunions.add(prov.reunion)

                if prov.locuteurs:
                    locuteurs.add(prov.locuteurs)

        chapitres = [
            e.texte for e in self.document.elements
            if e.type == TYPE_TITRE_1
        ]

        for combo, valeurs in (
            (self.filtre_reunion, sorted(reunions)),
            (self.filtre_chapitre, chapitres),
            (self.filtre_locuteur, sorted(locuteurs)),
        ):
            courant = combo.currentData()

            combo.blockSignals(True)
            combo.clear()

            combo.addItem(
                (
                    "Toutes les réunions"
                    if combo is self.filtre_reunion
                    else (
                        "Tous les chapitres"
                        if combo is self.filtre_chapitre
                        else "Tous les intervenants"
                    )
                ),
                None
            )

            for v in valeurs:
                combo.addItem(str(v), v)

            index = combo.findData(courant)

            combo.setCurrentIndex(
                index if index >= 0 else 0
            )

            combo.blockSignals(False)

    def _valeurs_filtres(self):

        return (
            self.filtre_reunion.currentData(),
            self.filtre_chapitre.currentData(),
            self.filtre_locuteur.currentData(),
        )

    def _element_dans_filtres(self, element) -> bool:

        reunion_f, chapitre_f, locuteur_f = (
            self._valeurs_filtres()
        )

        if chapitre_f is not None:

            # Chapitre courant de l'élément.
            courant = None

            for e in self.document.elements:

                if e.type == TYPE_TITRE_1:
                    courant = e.texte

                if e.id == element.id:
                    break

            if courant != chapitre_f:
                return False

        if reunion_f is not None and (
            reunion_f not in {
                p.reunion for p in element.provenances
            }
        ):
            return False

        if locuteur_f is not None and (
            locuteur_f not in {
                p.locuteurs for p in element.provenances
            }
        ):
            return False

        return True

    def _ajouter_noeud_paragraphe(self, parent, element):

        item = QTreeWidgetItem(
            [
                (element.texte or "")[:60].strip()
                or "Paragraphe"
            ]
        )

        item.setData(
            0,
            Qt.ItemDataRole.UserRole,
            element.id
        )

        parent.addChild(item)

        return item

    def _sur_clic_resultat(self, item):
        """
        Occurrence cliquable : amène le manuscrit au
        paragraphe correspondant (lien vers le
        paragraphe, P20.3/P20.6g).
        """

        identifiant = item.data(
            0,
            Qt.ItemDataRole.UserRole
        )

        if not identifiant:
            return

        editeur = self.editeurs.get(identifiant)

        if editeur is not None:

            self.manuscrit_defile.ensureWidgetVisible(
                editeur
            )

            editeur.setFocus()

    def _reappliquer_filtres(self, *args):

        if self._dernier_resultat is None:
            return

        type_resultat, donnees = self._dernier_resultat

        self._afficher_resultat(type_resultat, donnees)

    def _afficher_resultat(self, type_resultat, donnees):

        self._dernier_resultat = (type_resultat, donnees)

        self.resultats_arbre.clear()

        if self.document is None:
            return

        if type_resultat == "emphase":

            signales = set(donnees.get("signales") or [])

            for mot, total in donnees["totaux"].items():

                paragraphes_signales = [
                    pid for pid in total["paragraphes"]
                    if pid in signales
                ]

                # Seuls les intensifs signalés (densité
                # anormale dans un paragraphe, ou tic
                # inter-réunions) sont listés.
                if not paragraphes_signales and (
                    len(total["reunions"]) < 3
                ):
                    continue

                noeud = QTreeWidgetItem(
                    [
                        f"« {mot} » — "
                        f"{total['occurrences']} fois, "
                        f"{len(total['reunions'])} "
                        "réunion(s)"
                    ]
                )

                for pid in total["paragraphes"]:

                    element = self.document.element(pid)

                    if element is not None and (
                        self._element_dans_filtres(element)
                    ):
                        self._ajouter_noeud_paragraphe(
                            noeud,
                            element
                        )

                if noeud.childCount():
                    self.resultats_arbre.addTopLevelItem(
                        noeud
                    )

        elif type_resultat == "expressions":

            for famille in donnees:

                noeud = QTreeWidgetItem(
                    [
                        " / ".join(
                            famille["expressions"]
                        )
                        + f" — {famille['occurrences']} fois"
                    ]
                )

                for pid in famille["paragraphes"]:

                    element = self.document.element(pid)

                    if element is not None and (
                        self._element_dans_filtres(element)
                    ):
                        self._ajouter_noeud_paragraphe(
                            noeud,
                            element
                        )

                if noeud.childCount():
                    self.resultats_arbre.addTopLevelItem(
                        noeud
                    )

        elif type_resultat == "redondances":

            for i, groupe in enumerate(donnees, 1):

                noeud = QTreeWidgetItem(
                    [
                        f"Groupe {i} : "
                        + " — ".join(
                            p[:40]
                            for p in groupe["phrases"]
                        )
                        + (
                            ""
                            if groupe["paragraphes"]
                            else " (aucun paragraphe lié)"
                        )
                    ]
                )

                for pid in groupe["paragraphes"]:

                    element = self.document.element(pid)

                    if element is not None and (
                        self._element_dans_filtres(element)
                    ):
                        self._ajouter_noeud_paragraphe(
                            noeud,
                            element
                        )

                # Les groupes sont toujours affichés
                # (avec leurs liens vers les
                # paragraphes quand ils existent).
                self.resultats_arbre.addTopLevelItem(
                    noeud
                )

        self.resultats_arbre.expandAll()

    def afficher_emphases(self):
        """
        P20.3 : récurrence d'emphase — comptage des
        intensifs (lexique paramétrable) par
        paragraphe/réunion/intervenant, sur
        l'ouvrage. LOCAL, sans LLM.
        """

        if self.document is None:
            return

        from services.relecture import (
            emphase_ouvrage,
        )

        lexique = None

        bloc = (
            self.etude.parametres.controle_qualite
            or {}
        ).get("emphase") or {}

        if bloc.get("intensifs"):
            lexique = bloc["intensifs"]

        resultat = emphase_ouvrage(
            self.document,
            lexique=lexique
        )

        self._afficher_resultat("emphase", resultat)

        if not resultat["signales"]:

            QMessageBox.information(
                self,
                "Récurrence d'emphase",
                (
                    "Aucune densité anormale d'intensifs "
                    "signalée sur l'ouvrage."
                )
            )

    def afficher_expressions(self):
        """
        P20.3 : expressions récurrentes de l'ouvrage
        (n-grammes 2-6, deux signaux), regroupées en
        familles par mots communs. LOCAL, sans LLM ;
        la passe LLM optionnelle porte sur les
        seules familles candidates (à la demande).
        """

        if self.document is None:
            return

        from services.relecture import (
            expressions_recurrentes_ouvrage,
            familles_expressions,
        )

        candidates = expressions_recurrentes_ouvrage(
            self.document
        )

        familles = familles_expressions(candidates)

        self._afficher_resultat(
            "expressions",
            familles
        )

        if not familles:

            QMessageBox.information(
                self,
                "Expressions récurrentes",
                (
                    "Aucune expression récurrente "
                    "signalée (présence dans au moins "
                    "deux réunions)."
                )
            )

    def analyser_coherence(self):
        """
        P20.3 : incohérences/redondances de la
        section sélectionnée — passe LLM PAR
        SECTION, à la demande. Signalement
        uniquement.
        """

        titre, paragraphes = self._section_selection()

        if not paragraphes:

            QMessageBox.information(
                self,
                "Section vide",
                "Sélectionnez un élément d'une section "
                "comportant des paragraphes."
            )
            return

        from services.traitements.relecture import (
            ServiceRelecture,
        )

        service = ServiceRelecture(self.etude)

        textes = [p.texte for p in paragraphes]

        def appel():
            return service.analyser_section(textes)

        def on_ok(resultat):

            self._arreter_llm()

            rapport, stats = resultat

            QMessageBox.information(
                self,
                "Analyse de cohérence (signalement)",
                (
                    "Section « "
                    + (titre.texte if titre else "Réserves")
                    + " » :\n\n"
                    + rapport
                    + f"\n\n(coût réel : "
                    f"{stats.get('cout_estime', 0.0):.4f} $)"
                )
            )

        def on_err(message):

            self._arreter_llm()

            QMessageBox.warning(
                self,
                "Analyse non réalisée",
                message
            )

        self._lancer_llm(appel, on_ok, on_err)

    def detecter_pensees_redondantes(self):
        """
        P20.6g : détection des pensées redondantes —
        présélection LOCALE sans LLM (comparaison
        normalisée des phrases courtes de la
        synthèse), groupes reliés aux paragraphes
        de l'ouvrage (liens cliquables, provenance
        P19.1) ; confirmation par passe LLM À LA
        DEMANDE sur la seule liste candidate.
        Signalement uniquement, jamais de
        réécriture.
        """

        if self.document is None:
            return

        versions = self.etude.synthese.versions

        if not versions:

            QMessageBox.information(
                self,
                "Pensées redondantes",
                (
                    "Aucune synthèse d'étude : "
                    "alimentez-la d'abord (page Étude)."
                )
            )
            return

        from services.relecture import (
            lier_pensees_aux_paragraphes,
            preselectionner_pensees_redondantes,
        )

        synthese = versions[-1].texte

        groupes = preselectionner_pensees_redondantes(
            synthese
        )

        if not groupes:

            QMessageBox.information(
                self,
                "Pensées redondantes",
                (
                    "Présélection locale : aucune "
                    "pensée redondante dans la "
                    "synthèse (aucun coût LLM)."
                )
            )
            return

        groupes_lies = lier_pensees_aux_paragraphes(
            self.document,
            groupes
        )

        self._dernier_groupes = groupes

        self._afficher_resultat(
            "redondances",
            groupes_lies
        )

        reponse = QMessageBox.question(
            self,
            "Confirmation LLM ?",
            (
                f"{len(groupes)} groupe(s) candidat(s) "
                "présélectionnés localement (sans "
                "LLM).\n\nConfirmer par une passe LLM "
                "sur cette seule liste candidate "
                "(coût minuscule) ?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if reponse != QMessageBox.StandardButton.Yes:
            return

        from services.traitements.relecture import (
            ServiceRelecture,
        )

        service = ServiceRelecture(self.etude)

        def appel():
            return service.confirmer_redondances(
                groupes
            )

        def on_ok(resultat):

            self._arreter_llm()

            rapport, stats = resultat

            QMessageBox.information(
                self,
                "Confirmation des redondances",
                (
                    rapport
                    + f"\n\n(coût réel : "
                    f"{stats.get('cout_estime', 0.0):.4f} $)"
                )
            )

        def on_err(message):

            self._arreter_llm()

            QMessageBox.warning(
                self,
                "Confirmation non réalisée",
                message
            )

        self._lancer_llm(appel, on_ok, on_err)

    def reverifier_versets(self):
        """
        P20.5b : re-vérifie les références
        bibliques de l'ouvrage contre la RÉFÉRENCE
        D'UNIFORMITÉ (version ouvrage choisie dans
        ouvrage.json ; sinon version de l'étude).
        Écarts de versification = information
        (jamais de décision automatique). Contrôle
        local, sans LLM.
        """

        if self.document is None:
            return

        from services.bibles import (
            autres_versions_installees,
            charger_bible_version,
            nom_court_bible,
            version_bible_etude,
        )
        from services.jnd import extraire_references

        version = (
            getattr(
                self.document,
                "reference_bible",
                ""
            )
            or version_bible_etude(
                self.etude.parametres
            )
        )

        bible = charger_bible_version(version)

        autres = autres_versions_installees(version)

        lignes = [
            f"Re-vérification des versets contre "
            f"« {nom_court_bible(version)} » :"
        ]

        total = 0
        ecarts = 0

        for p in self.document.paragraphes():

            for ref in extraire_references(p.texte):

                total += 1

                existe = (
                    bible is not None
                    and bible.existe_reference(ref)
                )

                if not existe:

                    ecarts += 1

                    ailleurs = [
                        nom_court_bible(v)
                        for v, b in autres.items()
                        if b is not None
                        and b.existe_reference(ref)
                    ]

                    lignes.append(
                        f"· {ref} (paragraphe {p.id}) — "
                        "introuvable dans cette version"
                        + (
                            " ; existe dans : "
                            + ", ".join(ailleurs)
                            if ailleurs
                            else ""
                        )
                        + " (information)."
                    )

        lignes.append("")

        lignes.append(
            f"{total} référence(s) vérifiée(s), "
            f"{ecarts} écart(s) signalé(s) "
            "(information)."
        )

        self._versets_rapport = lignes

        self._reconstruire_rapport()

        QMessageBox.information(
            self,
            "Re-vérification des versets",
            "\n".join(lignes)
        )

    def _sur_texte_element(self, element, texte):
        """
        Édition en place : le texte de l'élément du
        document suit l'éditeur (l'ouvrage vit sa
        propre vie — il diverge des textes validés).
        """

        if element.texte == texte:
            return

        element.texte = texte

        self.modifie = True

        self.sauvegarder_button.setEnabled(True)

    def sauvegarder_document(self):
        """
        Écrit le document dans l'étude (ouvrage.json)
        — le dossier reste autonome et portable.
        """

        if self.document is None:
            return

        sauvegarder_ouvrage(
            self.document,
            self.etude.dossier
        )

        self.modifie = False

        self._maj_outils()

    # ==================================================
    # Navigation.
    # ==================================================

    def ouvrir_etude(self):

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if navigation is not None:
            navigation.ouvrir_etude(
                self.etude.dossier
            )

    def ouvrir_bible(self):
        """
        P18.10 : ouvre le lecteur de Bible intégré
        (pile unique — « Retour » ramène ici).
        """

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if (
            navigation is not None
            and hasattr(navigation, "ouvrir_bible")
        ):
            navigation.ouvrir_bible()
            return

        from ui.bible_window import BibleWindow

        self.fenetre_bible = BibleWindow(
            settings=self.settings
        )

        self.fenetre_bible.show()

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

    # ==================================================
    # Export final (P18.3).
    # ==================================================

    def exporter_document_docx(self):
        """
        P20.4 : export DOCX STRUCTURÉ du document
        ouvrage édité (styles Titre 1 / sous-titres ;
        métadonnées de réunion en note ou annexe
        selon le réglage de l'app). Fidèle à la
        structure éditée.
        """

        if self.document is None:

            QMessageBox.information(
                self,
                "Aucun ouvrage",
                "Générez d'abord le document ouvrage."
            )
            return

        from PySide6.QtWidgets import QRadioButton

        prefs = self.settings.get_export_ouvrage_prefs()

        dialogue = QDialog(self)
        dialogue.setWindowTitle(
            "Export DOCX structuré"
        )

        options = QVBoxLayout(dialogue)

        options.addWidget(
            QLabel(
                "Métadonnées de réunion (provenance "
                "des paragraphes) :"
            )
        )

        note_radio = QRadioButton(
            "En note (sous chaque paragraphe)"
        )

        annexe_radio = QRadioButton(
            "En annexe (section en fin de document)"
        )

        if prefs["metadonnees"] == "annexe":
            annexe_radio.setChecked(True)
        else:
            note_radio.setChecked(True)

        options.addWidget(note_radio)
        options.addWidget(annexe_radio)

        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        boutons.accepted.connect(dialogue.accept)
        boutons.rejected.connect(dialogue.reject)

        options.addWidget(boutons)

        if dialogue.exec() != (
            QDialog.DialogCode.Accepted
        ):
            return

        metadonnees = (
            "annexe"
            if annexe_radio.isChecked()
            else "note"
        )

        # Réglage mémorisé.
        self.settings.set_export_ouvrage_prefs(
            {"metadonnees": metadonnees}
        )

        import re as _re

        nom_defaut = _re.sub(
            r"[^\w\- ]",
            "",
            self.document.titre or "ouvrage"
        ).strip() or "ouvrage"

        chemin, _filtre = QFileDialog.getSaveFileName(
            self,
            "Exporter le document ouvrage (DOCX structuré)",
            str(
                self.etude.dossier
                / f"{nom_defaut}.docx"
            ),
            "Document Word (*.docx)"
        )

        if not chemin:
            return

        from services.bibles import (
            VERSIONS_BIBLE,
            version_bible_etude,
        )
        from services.export_ouvrage import (
            exporter_document_docx,
        )

        # Référence d'uniformité de l'ouvrage si
        # choisie (P20.5), sinon version de l'étude.
        version = (
            getattr(self.document, "reference_bible", "")
            or version_bible_etude(self.etude.parametres)
        )

        nom_bible = VERSIONS_BIBLE[version]["nom"]

        try:

            chemin = exporter_document_docx(
                self.document,
                chemin,
                metadonnees=metadonnees,
                bible=nom_bible,
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Export impossible",
                str(e)
            )

            return

        message = QMessageBox(self)
        message.setWindowTitle("Ouvrage exporté")
        message.setText(
            f"Le document ouvrage a été exporté :\n\n{chemin}"
        )

        open_file_button = message.addButton(
            "Ouvrir le fichier",
            QMessageBox.ButtonRole.AcceptRole
        )

        open_folder_button = message.addButton(
            "Ouvrir le dossier",
            QMessageBox.ButtonRole.AcceptRole
        )

        message.addButton(
            "Fermer",
            QMessageBox.ButtonRole.RejectRole
        )

        message.exec()

        clicked = message.clickedButton()

        if clicked is open_file_button:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(chemin))
            )

        elif clicked is open_folder_button:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(Path(chemin).parent)
                )
            )

    def exporter_ouvrage(self):
        """
        « Exporter… » : assemble les textes validés
        (résumés en tête de section si souhaité,
        reformulations dans l'ordre d'ouvrage) et
        exporte en DOCX (ou TXT). Flux P13 : message
        de fin avec ouverture du fichier ou du
        dossier.
        """

        import re as _re

        from services.export_ouvrage import (
            assembler_ouvrage,
            exporter_docx,
            exporter_txt,
        )

        apercu = assembler_ouvrage(
            self.etude,
            inclure_resumes=True,
            en_tetes_reunions=True
        )

        if not apercu["reunions"]:

            QMessageBox.information(
                self,
                "Rien à exporter",
                (
                    "Aucun texte validé dans l'étude : "
                    "validez des reformulations (ou un "
                    "résumé) avant d'exporter l'ouvrage."
                )
            )

            return

        dialogue = QDialog(self)
        dialogue.setWindowTitle("Exporter l'ouvrage")

        options = QVBoxLayout(dialogue)

        resumes_check = QCheckBox(
            "Inclure les résumés validés "
            "en tête de section"
        )
        resumes_check.setChecked(True)

        tetes_check = QCheckBox(
            "Titres de réunion"
        )
        tetes_check.setChecked(True)

        options.addWidget(resumes_check)
        options.addWidget(tetes_check)

        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        boutons.accepted.connect(dialogue.accept)
        boutons.rejected.connect(dialogue.reject)

        options.addWidget(boutons)

        if dialogue.exec() != (
            QDialog.DialogCode.Accepted
        ):
            return

        nom_defaut = _re.sub(
            r"[^\w\- ]",
            "",
            apercu["titre"]
        ).strip() or "ouvrage"

        chemin, filtre = QFileDialog.getSaveFileName(
            self,
            "Exporter l'ouvrage",
            str(
                self.etude.dossier
                / f"{nom_defaut}.docx"
            ),
            "Document Word (*.docx);;"
            "Texte (*.txt)"
        )

        if not chemin:
            return

        ouvrage = assembler_ouvrage(
            self.etude,
            inclure_resumes=(
                resumes_check.isChecked()
            ),
            en_tetes_reunions=(
                tetes_check.isChecked()
            )
        )

        try:

            if filtre.startswith("Document"):
                chemin = exporter_docx(
                    ouvrage,
                    chemin
                )
            else:
                chemin = exporter_txt(
                    ouvrage,
                    chemin
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Export impossible",
                str(e)
            )

            return

        message = QMessageBox(self)
        message.setWindowTitle("Ouvrage exporté")
        message.setText(
            f"L'ouvrage a été exporté :\n\n{chemin}"
        )

        open_file_button = message.addButton(
            "Ouvrir le fichier",
            QMessageBox.ButtonRole.AcceptRole
        )

        open_folder_button = message.addButton(
            "Ouvrir le dossier",
            QMessageBox.ButtonRole.AcceptRole
        )

        message.addButton(
            "Fermer",
            QMessageBox.ButtonRole.RejectRole
        )

        message.exec()

        clicked = message.clickedButton()

        if clicked is open_file_button:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(chemin))
            )

        elif clicked is open_folder_button:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(Path(chemin).parent)
                )
            )
