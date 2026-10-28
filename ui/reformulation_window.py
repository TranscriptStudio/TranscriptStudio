# ui/reformulation_window.py
"""
Page Traitement / Reformulation (P16.2, P16.2b).

Spécifications de référence :
- UI_REFORMULATION_V2.md (fait autorité) ;
- UI_REFORMULATION_MODIFS_V2_2026-10-27.md (correctifs
  de relecture P16-bis — PRIME sur la précédente pour
  ses points) ;
- SPEC_MOTEUR_P15_V2.md (exécution).

Table de relecture en lecture parallèle : une
ligne par bloc — colonne locuteurs (noms du bloc),
texte brut corrigé (lecture seule, audio et
timeline v1), bloc reformulé (éditable), pastille
d'état et indicateur de version à droite (menu des
opérations).

Correctifs P16-bis (spec MODIFS) :
- une seule barre de défilement verticale pour
  toute la table (les deux colonnes défilent
  ensemble) ; AUCUNE barre de défilement dans une
  cellule de bloc — les cellules s'étendent à la
  hauteur de leur contenu ;
- hauteur de ligne = hauteur max des deux cellules
  (brut ↔ reformulé alignés horizontalement, l'autre
  cellule se cale en haut), maintenue au fil de la
  frappe et au redimensionnement des colonnes ;
- colonne locuteurs = une cellule par ligne de bloc
  (noms, « / » pour un bloc fusionné) ; le filtrage
  est retiré de l'UI mais l'API est conservée
  (selectionner_locuteur / appliquer_filtrage),
  prête à être rebranchée plus tard sur un menu
  « Filtrer par locuteur… » de la barre supérieure ;
- la zone gauche de la timeline a exactement la
  largeur de la colonne locuteurs ;
- la taille du texte (A+/A−) et les largeurs de
  colonnes sont mémorisées dans les réglages
  (défaut abaissé pour la double colonne).

Règles d'invariance UI (spec §7) :
1. la colonne brute n'expose aucune commande de
   modification (ni active ni grisée) ;
2. aucune opération ne modifie le texte brut ;
3. l'alignement brut ↔ reformulé tient au
   redimensionnement ; la timeline ancrée en bas
   n'est pas affectée par le défilement ;
4. un bloc validé est figé (édition et relances
   verrouillées, versions consultables) ;
5. la validation n'est possible que sur une
   version sauvegardée ;
6. le filtrage par locuteur ne masque ni le
   traitement en cours ni la barre d'état.
"""

import re

from PySide6.QtCore import (
    QObject,
    Qt,
    QThread,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QColor,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTextEdit,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

from services.controle_qualite import controles_bloc
from services.etude_io import (
    EtudeOuverte,
    ajouter_version_reformulation,
    devalider_version_reformulation,
    fichier_projet_v1,
    valider_version_reformulation,
)
from services.etude_schema import EtudeFormatError
from services.project_io import load_project
from services.settings import SettingsManager
from services.timecodes import lire_timecode
from services.traitements.moteur import (
    CIBLE_NON_VALIDES,
    ErreurContexte,
    MoteurTraitements,
)
from services.playback import PlaybackManager
from ui.timeline_widget import TimelineWidget
from ui.timeline_speaker_panel import (
    TimelineSpeakerPanel
)

from pathlib import Path

try:
    import getpass

    VALIDATEUR_DEFAUT = getpass.getuser()
except Exception:
    VALIDATEUR_DEFAUT = "Utilisateur"


#
# Taille du texte : plage A+/A− inchangée, défaut
# abaissé pour la lecture en double colonne (spec
# correctifs §5).
#

TAILLE_TEXTE_MIN = 9
TAILLE_TEXTE_MAX = 24
TAILLE_TEXTE_DEFAUT = 11


#
# Couleurs des pastilles (spec §5) — toujours
# accompagnées d'un libellé textuel (tooltip).
#

COULEUR_NON_TRAITE = "#9E9E9E"
COULEUR_MODIFIABLE = "#2196F3"
COULEUR_EN_COURS = "#64B5F6"
COULEUR_VALIDEE = "#4CAF50"

ETAT_NON_TRAITE = "non_traite"
ETAT_MODIFIABLE = "modifiable"
ETAT_EN_COURS = "en_cours"
ETAT_VALIDEE = "validee"

LIBELLES_ETAT = {
    ETAT_NON_TRAITE: "Non traité",
    ETAT_MODIFIABLE: "Traité, non validé (modifiable)",
    ETAT_EN_COURS: "En cours de traitement",
    ETAT_VALIDEE: "Validé (figé)",
}


class ReformulationWorker(QObject):
    """
    Exécute une passe du moteur dans un thread :
    la page reste réactive, l'annulation est
    propre (B2 : tout résultat déjà produit est
    conservé).
    """

    progression = Signal(int, int)
    bloc_traite = Signal(int)
    terminee = Signal(object)

    erreur = Signal(str)

    def __init__(
        self,
        moteur: MoteurTraitements,
        annulation,
        cible: str
    ):
        super().__init__()

        self.moteur = moteur
        self.annulation = annulation
        self.cible = cible

    @Slot()
    def run(self):

        try:

            def avancer(fid, traites, total):
                self.progression.emit(traites, total)
                self.bloc_traite.emit(fid)

            resultat = (
                self.moteur.traiter_reunion(
                    annulation=self.annulation,
                    progression=avancer,
                    cible=self.cible
                )
            )

            self.terminee.emit(resultat)

        except ErreurContexte as e:
            self.erreur.emit(str(e))

        except Exception as e:
            self.erreur.emit(str(e))


class ReformulationBlocWorker(QObject):
    """
    Exécute une relance (complète ou ciblée) d'un
    seul bloc dans un thread.
    """

    terminee = Signal(int, object)
    erreur = Signal(int, str)

    def __init__(
        self,
        moteur: MoteurTraitements,
        fid: int,
        consigne=None,
        selection=None,
        annulation=None
    ):
        super().__init__()

        self.moteur = moteur
        self.fid = fid
        self.consigne = consigne
        self.selection = selection
        self.annulation = annulation

    @Slot()
    def run(self):

        try:

            version = (
                self.moteur.traiter_bloc(
                    self.fid,
                    consigne=self.consigne,
                    selection=self.selection,
                    annulation=self.annulation
                )
            )

            self.terminee.emit(self.fid, version)

        except Exception as e:
            self.erreur.emit(self.fid, str(e))


class LigneBloc:
    """
    Une ligne de la table de relecture : nom(s) du
    ou des locuteurs, texte brut (lecture seule),
    bloc reformulé (éditable), pastille d'état et
    indicateur de version.

    P16-bis : les cellules ne défilent jamais
    intérieurement (spec correctifs §1.1) — la
    hauteur de contenu est portée par la ligne de
    la table.
    """

    def __init__(
        self,
        bloc,
        taille_texte: int
    ):

        self.bloc = bloc

        #
        # État d'affichage de la ligne.
        #
        self.consultation = None
        self.non_enregistre = False
        self.filtration_locuteur = True

        #
        # Colonne locuteurs : le(s) nom(s) du bloc
        # (« / » pour un bloc fusionné
        # multi-locuteurs) — spec correctifs §2.1.
        #
        self.label_locuteurs = QLabel(
            " / ".join(bloc.locuteurs)
        )
        self.label_locuteurs.setWordWrap(True)
        self.label_locuteurs.setAlignment(
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignLeft
        )

        #
        # Texte brut corrigé : référence de
        # relecture, lecture seule PERMANENTE
        # (règles 1 et 2 : aucun menu, aucune
        # modification).
        #
        #
        # QTextEdit (et non QPlainTextEdit) : la
        # hauteur de contenu rendue par le layout
        # du document est exacte, ce qui permet
        # d'ajuster la hauteur de ligne sans
        # défilement interne.
        #
        self.cellule_brute = QTextEdit()
        self.cellule_brute.setAcceptRichText(False)
        self.cellule_brute.setReadOnly(True)
        self.cellule_brute.setPlainText(bloc.source)
        self.cellule_brute.setTabChangesFocus(True)
        self._sans_defilement_interne(
            self.cellule_brute
        )

        #
        # Bloc reformulé : éditable quand le bloc
        # n'est pas validé (règle 4).
        #
        self.cellule_reformee = QTextEdit()
        self.cellule_reformee.setAcceptRichText(False)
        self.cellule_reformee.setTabChangesFocus(
            True
        )
        self._sans_defilement_interne(
            self.cellule_reformee
        )

        #
        # Pastille d'état + indicateur de version
        # (spec §5), à droite de la ligne.
        #
        self.colonne_droite = QWidget()

        colonne_droite = QVBoxLayout(
            self.colonne_droite
        )
        colonne_droite.setContentsMargins(
            0, 0, 0, 0
        )
        colonne_droite.setSpacing(4)

        self.pastille = QToolButton()
        self.pastille.setText("●")
        self.pastille.setFixedSize(26, 26)
        self.pastille.setToolTip("État du bloc")

        self.version_label = QPushButton("—")
        self.version_label.setFixedWidth(130)
        self.version_label.setToolTip(
            "Versions du bloc (clic pour consulter)"
        )

        colonne_droite.addWidget(self.pastille)
        colonne_droite.addWidget(self.version_label)
        colonne_droite.addStretch()

        self.appliquer_taille(taille_texte)

        #
        # Mots de la ligne : pour le clic de
        # positionnement et le surlignage du mot lu
        # (E1.3). Rempli par la fenêtre depuis le
        # projet v1.
        #
        self.mots_ligne = []

        #
        # Jetons non-espaces de la cellule brute :
        # index du jeton <-> mot projeté.
        #
        self.jetons = list(
            re.finditer(r"\S+", bloc.source)
        )

    @staticmethod
    def _sans_defilement_interne(cellule):
        """
        Aucune barre de défilement dans une cellule
        de bloc (spec correctifs §1.1) : le retour à
        la ligne se fait sur la largeur de la
        colonne, la hauteur est portée par la ligne
        de la table.
        """

        cellule.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        cellule.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        cellule.setLineWrapMode(
            QTextEdit.LineWrapMode.WidgetWidth
        )

    def appliquer_taille(self, taille: int):

        for cellule in (
            self.cellule_brute,
            self.cellule_reformee,
        ):
            police = cellule.font()
            police.setPointSize(taille)
            cellule.setFont(police)

        police = self.label_locuteurs.font()
        police.setPointSize(max(9, taille - 1))
        self.label_locuteurs.setFont(police)

    def surligner_mot(self, index: int):
        """
        Surligne le jeton d'index donné dans la
        cellule brute (mot lu).
        """

        format_surlignage = QTextCharFormat()
        format_surlignage.setBackground(
            QColor("#FFF3B0")
        )

        if index is None or not self.mots_ligne:
            self.cellule_brute.setExtraSelections([])
            return

        if not (0 <= index < len(self.mots_ligne)):
            self.cellule_brute.setExtraSelections([])
            return

        debut, fin = self.mots_ligne[index]

        curseur = QTextCursor(
            self.cellule_brute.textCursor()
        )

        curseur.setPosition(0)
        curseur.setPosition(debut)
        curseur.setPosition(
            fin,
            QTextCursor.MoveMode.KeepAnchor
        )

        selection = QTextEdit.ExtraSelection()

        selection.format = format_surlignage
        selection.cursor = curseur

        self.cellule_brute.setExtraSelections(
            [selection]
        )


class ReformulationWindow(QWidget):
    """
    Page de traitement Reformulation d'une réunion.
    """

    def __init__(
        self,
        etude_ouverte: EtudeOuverte,
        nom_reunion: str,
        settings: SettingsManager = None
    ):
        super().__init__()

        self.etude = etude_ouverte
        self.reunion = nom_reunion

        #
        # Réglages injectables (tests : config
        # isolée, jamais la configuration réelle de
        # l'utilisateur) — P16-bis §5 : la taille du
        # texte et les largeurs de colonnes sont
        # mémorisées dans l'app.
        #
        self.settings = (
            settings
            if settings is not None
            else SettingsManager()
        )

        prefs = (
            self.settings.get_reformulation_prefs()
        )

        self.setWindowTitle(
            f"Reformulation — {nom_reunion}"
        )

        self.resize(1300, 850)

        #
        # Projet v1 de la réunion : audio, timeline
        # et mots horodatés. Mode dégradé si
        # introuvable (pas d'audio ni de timeline).
        #
        self.projet_v1 = None

        chemin_projet = fichier_projet_v1(
            etude_ouverte,
            nom_reunion
        )

        if chemin_projet is not None:

            try:
                self.projet_v1 = load_project(
                    str(chemin_projet)
                )
            except (EtudeFormatError, Exception):
                self.projet_v1 = None

        #
        # Moteur de traitement (P15.3) branché sur
        # la configuration réelle (catalogue, clés,
        # réglages).
        #
        self.moteur = MoteurTraitements(
            etude_ouverte,
            nom_reunion
        )

        self.taille_texte = prefs.get(
            "taille_texte",
            TAILLE_TEXTE_DEFAUT
        )

        self.annulation_passe = None
        self.passe_en_cours = False

        self.thread_passe = None
        self.worker_passe = None
        self.thread_bloc = None
        self.worker_bloc = None

        self.playback = PlaybackManager()

        self.lignes = {}
        self.rangees = {}
        self.locuteur_selectionne = None

        self.build_ui(prefs)

        self.construire_lignes()

        self.brancher_audio()

    #
    # ==================================================
    # Construction de l'interface.
    # ==================================================
    #

    def build_ui(self, prefs: dict):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 8)
        layout.setSpacing(8)

        #
        # Barre supérieure.
        #
        barre = QHBoxLayout()
        barre.setSpacing(8)

        self.sauvegarder_button = QPushButton(
            "💾 Sauvegarder"
        )
        self.sauvegarder_button.setToolTip(
            "Sauvegarder l'étude"
        )

        self.aide_button = QPushButton("❓ Aide")
        self.aide_button.setToolTip(
            "Ouvrir le manuel utilisateur"
        )

        self.accueil_button = QPushButton(
            "🏠 Accueil"
        )

        self.traiter_button = QPushButton(
            "▶ Traiter les blocs non validés"
        )
        self.traiter_button.setToolTip(
            "Lance la passe sur les blocs non validés "
            "(l'estimation de coût est affichée à la fin "
            "de la passe ; aucune confirmation par bloc)"
        )

        self.couts_button = QPushButton("💶 Coûts")
        self.couts_button.setToolTip(
            "Estimation du coût de la passe (catalogue "
            "de coûts des réglages)"
        )

        self.annuler_button = QPushButton("⏹ Annuler")
        self.annuler_button.setVisible(False)
        self.annuler_button.setToolTip(
            "Interrompre la passe : tout ce qui est déjà "
            "produit est conservé"
        )

        self.augmenter_button = QPushButton("A+")
        self.diminuer_button = QPushButton("A−")

        self.log_button = QPushButton("📋 Log")
        self.log_button.setToolTip(
            "Log des opérations de l'étude (lecture seule)"
        )

        self.timeline_button = QPushButton("⏱ Timeline")
        self.timeline_button.setCheckable(True)
        self.timeline_button.setChecked(True)
        self.timeline_button.setToolTip(
            "Afficher ou masquer la timeline"
        )

        self.jouer_button = QPushButton("▶ Audio")
        self.jouer_button.setToolTip(
            "Lire / mettre en pause l'audio de la réunion"
        )

        for bouton in (
            self.sauvegarder_button,
            self.aide_button,
            self.accueil_button,
            self.traiter_button,
            self.couts_button,
            self.annuler_button,
        ):
            barre.addWidget(bouton)

        barre.addStretch()

        for bouton in (
            self.augmenter_button,
            self.diminuer_button,
            self.jouer_button,
            self.timeline_button,
            self.log_button,
        ):
            barre.addWidget(bouton)

        layout.addLayout(barre)

        #
        # Corps : table de relecture (P16-bis : une
        # seule barre de défilement verticale pour
        # toute la table, colonnes redimensionnables).
        #
        self.table = QTableWidget(0, 4)
        self._configurer_table(prefs)

        layout.addWidget(self.table, stretch=1)

        #
        # Timeline v1 (composant inchangé, ancré en
        # bas, masquable — règle 3).
        #
        self.conteneur_timeline = QWidget()

        timeline_layout = QHBoxLayout(
            self.conteneur_timeline
        )
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(0)

        if self.projet_v1 is not None:

            self.timeline = TimelineWidget(
                self.projet_v1
            )

            self.timeline_speakers = (
                TimelineSpeakerPanel(self.projet_v1)
            )

            #
            # La zone gauche de la timeline a
            # exactement la largeur de la colonne
            # locuteurs (spec correctifs §3) — le bord
            # gauche de la timeline s'aligne sur le
            # bord gauche des colonnes de texte.
            #
            self.timeline_speakers.setFixedWidth(
                self.table.columnWidth(0)
            )

            zone_timeline = QScrollArea()
            zone_timeline.setWidgetResizable(True)
            zone_timeline.setFixedHeight(160)
            zone_timeline.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOn
            )

            contenu_timeline = QWidget()
            contenu = QHBoxLayout(contenu_timeline)
            contenu.setContentsMargins(0, 0, 0, 0)
            contenu.setSpacing(0)

            contenu.addWidget(self.timeline_speakers)
            contenu.addWidget(self.timeline, stretch=1)

            zone_timeline.setWidget(contenu_timeline)

            timeline_layout.addWidget(zone_timeline)

        layout.addWidget(self.conteneur_timeline)

        #
        # Barre d'état : étude · réunion · validés /
        # total · progression (jamais masquée par le
        # filtrage — règle 6).
        #
        self.barre_etat = QLabel("")
        layout.addWidget(self.barre_etat)

        #
        # Connexions.
        #
        self.sauvegarder_button.clicked.connect(
            self.sauvegarder_etude
        )

        from services.help import open_user_manual

        self.aide_button.clicked.connect(
            open_user_manual
        )

        self.accueil_button.clicked.connect(
            self.retour_accueil
        )

        self.traiter_button.clicked.connect(
            self.lancer_traitement
        )

        self.couts_button.clicked.connect(
            self.afficher_couts_estimes
        )

        self.annuler_button.clicked.connect(
            self.annuler_traitement
        )

        self.augmenter_button.clicked.connect(
            lambda: self.changer_taille(1)
        )

        self.diminuer_button.clicked.connect(
            lambda: self.changer_taille(-1)
        )

        self.log_button.clicked.connect(
            self.ouvrir_log
        )

        self.timeline_button.toggled.connect(
            self.conteneur_timeline.setVisible
        )

        self.jouer_button.clicked.connect(
            self.basculer_lecture
        )

    def _configurer_table(self, prefs: dict):
        """
        Table de relecture P16-bis (spec correctifs
        §1) : une seule barre de défilement verticale
        pour toute la table (les deux colonnes
        défilent ensemble), lignes à hauteur
        variable ajustées au contenu (jamais de
        hauteur fixe), colonnes redimensionnables
        dont les largeurs sont mémorisées.
        """

        self.table.setHorizontalHeaderLabels([
            "Locuteurs",
            "Texte brut corrigé (v1)",
            "Bloc reformulé (LLM)",
            "",
        ])

        self.table.verticalHeader().setVisible(False)

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger
            .NoEditTriggers
        )

        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode
            .NoSelection
        )

        self.table.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        entete = self.table.horizontalHeader()

        entete.setSectionsMovable(False)

        entete.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Interactive
        )
        entete.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Interactive
        )
        entete.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch
        )
        entete.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Interactive
        )

        self.table.setColumnWidth(
            0,
            prefs.get("largeur_locuteurs") or 130
        )

        if prefs.get("largeur_brute"):
            self.table.setColumnWidth(
                1,
                prefs["largeur_brute"]
            )

        self.table.setColumnWidth(
            3,
            prefs.get("largeur_pastilles") or 160
        )

        entete.sectionResized.connect(
            self._sur_section_resized
        )

    def _sur_section_resized(
        self,
        index: int,
        _ancienne: int,
        nouvelle: int
    ):
        """
        Redimensionnement d'une colonne : la zone
        gauche de la timeline suit la colonne
        locuteurs (spec correctifs §3) ; les lignes
        se réétalent au nouveau retour à la ligne
        (§1.4).
        """

        if index == 0:

            if (
                getattr(
                    self, "timeline_speakers", None
                )
                is not None
            ):
                self.timeline_speakers.setFixedWidth(
                    int(nouvelle)
                )

        elif index in (1, 2):

            for fid in self.lignes:
                self._ajuster_hauteur_ligne(fid)

    @staticmethod
    def _hauteur_cellule(cellule) -> int:
        """
        Hauteur nécessaire à une cellule pour montrer
        tout son contenu sans barre de défilement
        (retour à la ligne à la largeur courante de
        la colonne).
        """

        document = cellule.document()

        hauteur = (
            document.documentLayout()
            .documentSize()
            .height()
        )

        marges = cellule.contentsMargins()

        hauteur += (
            2 * cellule.frameWidth()
            + marges.top()
            + marges.bottom()
        )

        return int(hauteur) + 4

    def _ajuster_hauteur_ligne(self, fid: int):
        """
        Hauteur de ligne = hauteur max des deux
        cellules du bloc (spec correctifs §1.3) :
        la ligne s'aligne sur la plus haute, l'autre
        cellule se cale en haut.
        """

        ligne = self.lignes.get(fid)

        if ligne is None:
            return

        rangée = self.rangees.get(fid)

        if rangée is None:
            return

        hauteur = max(
            self._hauteur_cellule(
                ligne.cellule_brute
            ),
            self._hauteur_cellule(
                ligne.cellule_reformee
            ),
            ligne.colonne_droite.sizeHint().height(),
            ligne.label_locuteurs.sizeHint().height(),
            56,
        )

        self.table.setRowHeight(rangée, hauteur)

    def blocs_actifs(self) -> list:

        from services.decoupage import blocs_actifs

        return blocs_actifs(self.etude, self.reunion)

    #
    # ==================================================
    # Lignes de la table.
    # ==================================================
    #

    def construire_lignes(self):
        """
        Construit une ligne par bloc actif, dans
        l'ordre chronologique (tri figé, spec §6).
        """

        for bloc in self.blocs_actifs():

            rangée = self.table.rowCount()
            self.table.insertRow(rangée)

            ligne = LigneBloc(
                bloc,
                self.taille_texte
            )

            self.lignes[bloc.fid] = ligne
            self.rangees[bloc.fid] = rangée

            self.table.setCellWidget(
                rangée, 0, ligne.label_locuteurs
            )
            self.table.setCellWidget(
                rangée, 1, ligne.cellule_brute
            )
            self.table.setCellWidget(
                rangée, 2, ligne.cellule_reformee
            )
            self.table.setCellWidget(
                rangée, 3, ligne.colonne_droite
            )

            self.brancher_ligne(ligne)

            self.projeter_mots(ligne)

            self.rafraichir_ligne(bloc.fid)

            #
            # La hauteur de ligne suit le contenu au
            # fil de la frappe et au retournement de
            # ligne (spec correctifs §1.4).
            #
            (
                ligne.cellule_brute
                .document()
                .documentLayout()
                .documentSizeChanged
                .connect(
                    lambda _taille, fid=bloc.fid:
                    self._ajuster_hauteur_ligne(fid)
                )
            )

            (
                ligne.cellule_reformee
                .document()
                .documentLayout()
                .documentSizeChanged
                .connect(
                    lambda _taille, fid=bloc.fid:
                    self._ajuster_hauteur_ligne(fid)
                )
            )

            self._ajuster_hauteur_ligne(bloc.fid)

        self.maj_barre_etat()

    def projeter_mots(self, ligne: LigneBloc):
        """
        Projette les mots horodatés du projet v1 sur
        la ligne (clic de positionnement + mot lu
        surligné, E1.3).
        """

        ligne.mots = {}

        if self.projet_v1 is None:
            ligne.mots_ligne = []
            return

        debut = lire_timecode(ligne.bloc.positions.debut)
        fin = lire_timecode(ligne.bloc.positions.fin)

        mots = []

        for mot in self.projet_v1.words:

            if mot.is_deleted:
                continue

            if mot.item_type == "spacing":
                continue

            if mot.start is None:
                continue

            if debut <= mot.start < fin:
                mots.append(mot)

        ligne.mots = mots

        #
        # Jetons de la cellule brute : index du
        # jeton ↔ mot projeté (les deux comptent
        # des séquences non-espaces ; en cas
        # d'écart, pas de projection mot à mot).
        #
        if len(mots) == len(ligne.jetons):

            ligne.mots_ligne = [
                (jeton.start(), jeton.end())
                for jeton in ligne.jetons
            ]

        else:
            ligne.mots_ligne = []

    def brancher_ligne(self, ligne: LigneBloc):

        fid = ligne.bloc.fid

        ligne.pastille.clicked.connect(
            lambda: self.ouvrir_menu_pastille(fid)
        )

        ligne.version_label.clicked.connect(
            lambda: self.ouvrir_menu_versions(fid)
        )

        ligne.cellule_reformee.textChanged.connect(
            lambda: self.sur_texte_change(fid)
        )

        #
        # Clic dans la colonne brute : positionner
        # le curseur de lecture (règle 1 : seule
        # action avec la timeline).
        #
        ligne.cellule_brute.mousePressEvent = (
            self._clic_cellule_brute(ligne)
        )

        ligne.cellule_reformee.contextMenuEvent = (
            lambda event: self.ouvrir_menu_pastille(
                fid
            )
        )

    def _clic_cellule_brute(self, ligne: LigneBloc):
        """
        Gestionnaire de clic dans la cellule brute :
        place le focus, puis positionne l'audio sur
        le mot cliqué.
        """

        def gestionnaire(event):

            cellule = ligne.cellule_brute

            curseur = cellule.cursorForPosition(
                event.pos()
            )

            position_caractere = curseur.position()

            self.positionner_audio(ligne, position_caractere)

            QTextEdit.mousePressEvent(
                cellule,
                event
            )

        return gestionnaire

    def positionner_audio(
        self,
        ligne: LigneBloc,
        position_caractere: int
    ):
        """
        Positionne la lecture sur le mot de la
        cellule brute le plus proche du clic (E1.3 :
        clic dans le texte = positionnement audio).
        """

        if not ligne.mots_ligne:
            position = lire_timecode(
                ligne.bloc.positions.debut
            )

        else:

            index = None

            for i, (debut, fin) in enumerate(
                ligne.mots_ligne
            ):
                if position_caractere <= fin:
                    index = i
                    break

            if index is None:
                index = len(ligne.mots_ligne) - 1

            position = lire_timecode(
                ligne.bloc.positions.debut
            )

            if index < len(ligne.mots):

                mot = ligne.mots[index]

                if mot.start is not None:
                    position = float(mot.start)

        self.playback.set_position(position)
        self.jouer_audio_si_charge()

    #
    # ==================================================
    # Rafraîchissement des états.
    # ==================================================
    #

    def versions_bloc(self, fid: int):

        resultat = self.etude.reformulations.get(fid)

        if not resultat:
            return []

        return resultat.versions

    def derniere_version(self, fid: int):

        versions = self.versions_bloc(fid)

        if not versions:
            return None

        return versions[-1]

    def etat_bloc(self, fid: int) -> str:

        versions = self.versions_bloc(fid)

        if not versions:
            return ETAT_NON_TRAITE

        derniere = versions[-1]

        if (
            derniere.validation
            and derniere.validation.statut == "valide"
        ):
            return ETAT_VALIDEE

        return ETAT_MODIFIABLE

    def libelle_version(self, version) -> str:

        numero = version.numero

        stats = version.stats

        if not stats:
            return f"v{numero} · édition"

        duree = stats.get("duree_ms", 0)
        tokens_in = stats.get("tokens_in", 0)
        tokens_out = stats.get("tokens_out", 0)
        cout = stats.get("cout_estime", 0.0)

        return (
            f"v{numero} · "
            f"{round(duree / 1000)}s · "
            f"{self._courte(tokens_in)}→"
            f"{self._courte(tokens_out)} · "
            f"{cout:.2f} €"
        )

    @staticmethod
    def _courte(tokens: int) -> str:

        if tokens >= 1000:
            return f"{tokens / 1000:.1f}k"

        return str(tokens)

    def rafraichir_ligne(self, fid: int):
        """
        Met à jour pastille, indicateur de version,
        éditabilité (règle 4 : bloc validé figé) et
        indicateurs de contrôle qualité.
        """

        ligne = self.lignes.get(fid)

        if ligne is None:
            return

        versions = self.versions_bloc(fid)
        derniere = self.derniere_version(fid)
        etat = self.etat_bloc(fid)

        #
        # Pastille : couleur + libellé textuel
        # (accessibilité, spec §6).
        #
        couleurs = {
            ETAT_NON_TRAITE: COULEUR_NON_TRAITE,
            ETAT_MODIFIABLE: COULEUR_MODIFIABLE,
            ETAT_EN_COURS: COULEUR_EN_COURS,
            ETAT_VALIDEE: COULEUR_VALIDEE,
        }

        ligne.pastille.setStyleSheet(
            f"color: {couleurs[etat]}; font-size: 20px;"
            " border: none; background: transparent;"
        )

        if ligne.non_enregistre:
            libelle = (
                LIBELLES_ETAT[etat]
                + " — modifications non enregistrées"
            )
        else:
            libelle = LIBELLES_ETAT[etat]

        ligne.pastille.setToolTip(libelle)

        #
        # Indicateur de version (affichage
        # permanent, spec §5).
        #
        if ligne.consultation is not None:
            ligne.version_label.setText(
                f"v{ligne.consultation} (consultée)"
            )
        elif derniere is not None:
            ligne.version_label.setText(
                self.libelle_version(derniere)
            )
        else:
            ligne.version_label.setText("—")

        #
        # Contenu de la cellule reformulée : version
        # courante (ou version consultée), jamais
        # modifiée par le rafraîchissement tant que
        # des modifications non enregistrées
        # existent.
        #
        if not ligne.non_enregistre:

            if ligne.consultation is not None:

                version_consultee = next(
                    (
                        v
                        for v in versions
                        if v.numero == ligne.consultation
                    ),
                    None
                )

                texte = (
                    version_consultee.texte
                    if version_consultee
                    else ""
                )

            else:
                texte = (
                    derniere.texte if derniere else ""
                )

            ligne.cellule_reformee.setPlainText(texte)

        #
        # Règle 4 : bloc validé (ou version
        # consultée) = figé.
        #
        fige = (
            etat == ETAT_VALIDEE
            or ligne.consultation is not None
        )

        ligne.cellule_reformee.setReadOnly(fige)

        self.appliquer_filtrage(ligne)

    def maj_barre_etat(self):
        """
        Barre d'état : étude · réunion · validés /
        total (jamais masquée par le filtrage —
        règle 6).
        """

        fids = list(self.lignes.keys())

        valides = sum(
            1
            for fid in fids
            if self.etat_bloc(fid) == ETAT_VALIDEE
        )

        self.barre_etat.setText(
            f"Étude : {self.etude.etude.titre} · "
            f"Réunion : {self.reunion} · "
            f"Blocs validés : {valides} / {len(fids)}"
        )

    def sur_texte_change(self, fid: int):
        """
        Modification non enregistrée : indicateur
        visuel sur la cellule (spec §4).
        """

        ligne = self.lignes.get(fid)

        if ligne is None:
            return

        derniere = self.derniere_version(fid)

        texte_courant = (
            ligne.cellule_reformee.toPlainText()
        )

        texte_version = (
            derniere.texte if derniere else ""
        )

        non_enregistre = (
            texte_courant != texte_version
            and ligne.consultation is None
        )

        if non_enregistre != ligne.non_enregistre:

            ligne.non_enregistre = non_enregistre

            ligne.cellule_reformee.setStyleSheet(
                "border: 1px solid #E65100;"
                if non_enregistre
                else ""
            )

            self.rafraichir_ligne(fid)

    #
    # ==================================================
    # Menus (pastille et versions).
    # ==================================================
    #

    def ouvrir_menu_pastille(self, fid: int):
        """
        Menu des opérations du bloc (spec §5) :
        éditer, sauvegarder, retour arrière,
        reformuler (complet / sélection), valider /
        dévalider.
        """

        ligne = self.lignes.get(fid)

        if ligne is None:
            return

        etat = self.etat_bloc(fid)

        menu = QMenu(self)

        validee = etat == ETAT_VALIDEE

        action_editer = menu.addAction(
            "Éditer le bloc"
        )

        action_sauvegarder = menu.addAction(
            "Sauvegarder le bloc "
            "(nouvelle version)"
        )

        action_retour = menu.addAction(
            "Retour arrière sur les modifications"
        )

        menu.addSeparator()

        action_reformuler = menu.addAction(
            "Reformuler le bloc…"
        )

        action_selection = menu.addAction(
            "Reformuler le texte sélectionné…"
        )

        menu.addSeparator()

        action_valider = menu.addAction(
            "Valider le bloc"
        )

        action_devalider = menu.addAction(
            "Dévalider le bloc"
        )

        #
        # Items indisponibles non affichés (spec
        # §5) : bloc validé → uniquement consulter
        # et dévalider.
        #
        if validee:

            action_editer.setVisible(False)
            action_sauvegarder.setVisible(False)
            action_retour.setVisible(False)
            action_reformuler.setVisible(False)
            action_selection.setVisible(False)
            action_valider.setVisible(False)

        else:

            action_devalider.setVisible(False)

            action_sauvegarder.setEnabled(
                ligne.non_enregistre
            )

            action_retour.setEnabled(
                ligne.non_enregistre
                or len(self.versions_bloc(fid)) > 1
            )

            if ligne.consultation is not None:
                action_editer.setVisible(False)
                action_sauvegarder.setVisible(False)
                action_reformuler.setVisible(False)
                action_selection.setVisible(False)

        action = menu.exec(
            ligne.pastille.mapToGlobal(
                ligne.pastille.rect().bottomLeft()
            )
        )

        if action == action_editer:
            ligne.cellule_reformee.setFocus()

        elif action == action_sauvegarder:
            self.sauvegarder_bloc(fid)

        elif action == action_retour:
            self.retour_arriere(fid)

        elif action == action_reformuler:
            self.reformuler_bloc(fid)

        elif action == action_selection:
            self.reformuler_selection(fid)

        elif action == action_valider:
            self.valider_bloc(fid)

        elif action == action_devalider:
            self.devalider_bloc(fid)

    def ouvrir_menu_versions(self, fid: int):
        """
        Menu déroulant des versions : la sélection
        remplace l'affichage de la cellule (version
        consultée, non éditable — règle 4) ; un
        retour à la version courante est toujours
        proposé.
        """

        ligne = self.lignes.get(fid)

        if ligne is None:
            return

        versions = self.versions_bloc(fid)

        if not versions:
            QToolTip.showText(
                ligne.version_label.mapToGlobal(
                    ligne.version_label.rect().bottomLeft()
                ),
                "Aucune version.",
            )
            return

        menu = QMenu(self)

        action_courante = menu.addAction(
            "Version courante (éditable)"
        )

        menu.addSeparator()

        actions = {}

        for version in versions:

            action = menu.addAction(
                f"v{version.numero} · {version.type} — "
                f"{self.libelle_version(version)[3:]}"
            )

            actions[action] = version.numero

        action = menu.exec(
            ligne.version_label.mapToGlobal(
                ligne.version_label.rect().bottomLeft()
            )
        )

        if action is None:
            return

        if action == action_courante:
            ligne.consultation = None
        else:
            ligne.consultation = actions[action]

        ligne.non_enregistre = False

        self.rafraichir_ligne(fid)

    #
    # ==================================================
    # Opérations de bloc.
    # ==================================================
    #

    def sauvegarder_bloc(self, fid: int):
        """
        Sauvegarde de l'édition : crée une version
        edition_manuelle (chaque sauvegarde = une
        nouvelle version, contrat §7).
        """

        ligne = self.lignes.get(fid)

        if ligne is None or ligne.consultation is not None:
            return

        if not ligne.non_enregistre:
            return

        ajouter_version_reformulation(
            self.etude,
            fid,
            ligne.cellule_reformee.toPlainText(),
            type_version="edition_manuelle",
        )

        ligne.non_enregistre = False

        self.sauvegarder_etude()

        self.rafraichir_ligne(fid)
        self.maj_barre_etat()

    def retour_arriere(self, fid: int):
        """
        Retour arrière : annule les modifications non
        sauvegardées (retour à la dernière version) ;
        une seconde invocation propose les versions
        antérieures (navigation dans l'historique,
        base de travail non enregistrée).
        """

        ligne = self.lignes.get(fid)

        if ligne is None:
            return

        if ligne.non_enregistre:

            derniere = self.derniere_version(fid)

            ligne.consultation = None
            ligne.non_enregistre = False

            ligne.cellule_reformee.setPlainText(
                derniere.texte if derniere else ""
            )

            self.rafraichir_ligne(fid)

            return

        #
        # Pas de modifications en attente :
        # proposer les versions antérieures comme
        # base de travail.
        #
        versions = self.versions_bloc(fid)

        if len(versions) < 2:
            return

        numeros = [
            f"v{v.numero} ({v.type})"
            for v in versions[:-1]
        ]

        choix, ok = QInputDialog.getItem(
            self,
            "Revenir à une version antérieure",
            "Version de base (non enregistrée tant "
            "qu'elle n'est pas sauvegardée) :",
            numeros,
            len(numeros) - 1,
            False
        )

        if not ok:
            return

        index = numeros.index(choix)

        version = versions[index]

        ligne.consultation = None

        ligne.cellule_reformee.setPlainText(
            version.texte
        )

        self.sur_texte_change(fid)

    def reformuler_bloc(self, fid: int):
        """
        Reformulation complète avec consigne
        complémentaire (optionnelle) — version
        relance. Aucune confirmation (B1) :
        exécution directe.
        """

        consigne, ok = QInputDialog.getText(
            self,
            "Reformuler le bloc",
            "Consigne complémentaire (facultative) :\n"
            "(ex. : plus concis, garder la question "
            "rhétorique…)",
        )

        if not ok:
            return

        self.lancer_relance(
            fid,
            consigne=consigne.strip() or None,
            selection=None
        )

    def reformuler_selection(self, fid: int):
        """
        Reformulation ciblée sur la sélection : le
        passage reformé est intégré au bloc complet ;
        c'est l'ensemble du bloc qui est versionné
        (relance_ciblee, spec §4).
        """

        ligne = self.lignes.get(fid)

        if ligne is None:
            return

        curseur = (
            ligne.cellule_reformee.textCursor()
        )

        if not curseur.hasSelection():
            QMessageBox.information(
                self,
                "Aucune sélection",
                "Sélectionnez d'abord le passage à "
                "reformuler dans le bloc."
            )
            return

        consigne, ok = QInputDialog.getText(
            self,
            "Reformuler le texte sélectionné",
            "Consigne complémentaire (facultative) :",
        )

        if not ok:
            return

        selection = {
            "debut": curseur.selectionStart(),
            "fin": curseur.selectionEnd(),
        }

        self.lancer_relance(
            fid,
            consigne=consigne.strip() or None,
            selection=selection
        )

    def lancer_relance(
        self,
        fid: int,
        consigne,
        selection
    ):
        """
        Relance d'un bloc dans un thread (réseau).
        """

        ligne = self.lignes.get(fid)

        if ligne is None:
            return

        #
        # Modifications non enregistrées : les
        # sauvegarder d'abord (la relance travaille
        # sur la version courante).
        #
        if ligne.non_enregistre:
            self.sauvegarder_bloc(fid)

        #
        # Pastille « en cours de traitement »
        # (spec §5 : bleue animée — transitoire).
        #
        ligne.pastille.setStyleSheet(
            f"color: {COULEUR_EN_COURS}; "
            "font-size: 20px; border: none; "
            "background: transparent;"
        )

        ligne.pastille.setToolTip(
            LIBELLES_ETAT[ETAT_EN_COURS]
        )

        self.thread_bloc = QThread(self)
        self.worker_bloc = ReformulationBlocWorker(
            self.moteur,
            fid,
            consigne=consigne,
            selection=selection
        )

        self.worker_bloc.moveToThread(self.thread_bloc)

        self.thread_bloc.started.connect(
            self.worker_bloc.run
        )

        self.worker_bloc.terminee.connect(
            self.sur_relance_terminee
        )

        self.worker_bloc.terminee.connect(
            self.thread_bloc.quit
        )

        self.worker_bloc.erreur.connect(
            self.sur_relance_erreur
        )

        self.worker_bloc.erreur.connect(
            self.thread_bloc.quit
        )

        self.thread_bloc.start()

    def sur_relance_terminee(self, fid: int, _version):

        ligne = self.lignes.get(fid)

        if ligne is not None:

            ligne.consultation = None
            ligne.non_enregistre = False

            self.rafraichir_ligne(fid)

        self.thread_bloc = None
        self.worker_bloc = None

        self.maj_barre_etat()

    def sur_relance_erreur(self, fid: int, message: str):

        QMessageBox.critical(
            self,
            "Reformulation impossible",
            message
        )

        ligne = self.lignes.get(fid)

        if ligne is not None:
            self.rafraichir_ligne(fid)

        self.thread_bloc = None
        self.worker_bloc = None

    def valider_bloc(self, fid: int):
        """
        Règle 5 : la validation n'est possible que
        sur une version sauvegardée (proposition de
        sauvegarder d'abord).
        """

        ligne = self.lignes.get(fid)

        if ligne is None:
            return

        versions = self.versions_bloc(fid)

        if not versions:
            return

        if ligne.non_enregistre:

            reponse = QMessageBox.question(
                self,
                "Modifications non enregistrées",
                (
                    "Le bloc comporte des modifications "
                    "non enregistrées.\n\n"
                    "Les sauvegarder avant de valider "
                    "(elles deviendront la version "
                    "validée) ?"
                )
            )

            if (
                reponse
                == QMessageBox.StandardButton.Yes
            ):
                self.sauvegarder_bloc(fid)
            else:
                return

        derniere = self.derniere_version(fid)

        valider_version_reformulation(
            self.etude,
            fid,
            numero=derniere.numero,
            validateur=VALIDATEUR_DEFAUT
        )

        #
        # Aucune relance en cascade (B3) :
        # l'utilisateur retouche individuellement
        # les blocs qu'il veut.
        #

        self.sauvegarder_etude()

        self.rafraichir_ligne(fid)
        self.maj_barre_etat()

        #
        # P17.2 : quand la réunion devient entièrement
        # validée, la synthèse d'étude se met à jour
        # (déclencheur « validation_bloc », contrat §9).
        #
        self.maj_synthese_si_reunion_validee()

    def devalider_bloc(self, fid: int):

        derniere = self.derniere_version(fid)

        if derniere is None:
            return

        devalider_version_reformulation(
            self.etude,
            fid,
            numero=derniere.numero
        )

        self.sauvegarder_etude()

        self.rafraichir_ligne(fid)
        self.maj_barre_etat()

    def maj_synthese_si_reunion_validee(self):
        """
        P17.2 : la synthèse d'étude se met à jour quand
        la réunion devient entièrement validée
        (tous ses blocs actifs validés) — déclencheur
        « validation_bloc » du contrat §9. Génération
        en arrière-plan, coût marginal affiché dans
        la barre d'état.
        """

        from services.traitements.synthese import (
            ServiceSynthese,
            reunion_entierement_validee,
        )
        from ui.etude_window import SyntheseWorker

        if getattr(self, "synthese_thread", None):
            return

        if not reunion_entierement_validee(
            self.etude,
            self.reunion
        ):
            return

        service = ServiceSynthese(self.etude)

        self.barre_etat.setText(
            "Réunion entièrement validée : "
            "mise à jour de la synthèse d'étude…"
        )

        self.synthese_thread = QThread(self)
        self.synthese_worker = SyntheseWorker(
            service,
            "validation_bloc"
        )

        self.synthese_worker.moveToThread(
            self.synthese_thread
        )

        self.synthese_thread.started.connect(
            self.synthese_worker.run
        )

        self.synthese_worker.terminee.connect(
            self._sur_synthese_terminee
        )
        self.synthese_worker.erreur.connect(
            self._sur_synthese_erreur
        )

        self.synthese_thread.start()

    def _sur_synthese_terminee(self, resultat):

        version, stats = resultat

        self.synthese_thread.quit()
        self.synthese_thread = None
        self.synthese_worker = None

        cout = stats.get("cout_estime", 0.0)

        self.barre_etat.setText(
            f"Synthèse d'étude v{version.numero} "
            f"générée (coût réel : {cout:.4f} $)."
        )

    def _sur_synthese_erreur(self, message):

        self.synthese_thread.quit()
        self.synthese_thread = None
        self.synthese_worker = None

        self.barre_etat.setText(
            "Synthèse d'étude non mise à jour : "
            + message
        )

    #
    # ==================================================
    # Passe complète (Traiter les blocs non validés).
    # ==================================================
    #

    def lancer_traitement(self):
        """
        Lance la passe sur les blocs non validés :
        pas de confirmation (B1 — le coût réel
        affiché en fin de passe fait office de
        confirmation de la passe suivante) ;
        annulation propre (B2).
        """

        if self.passe_en_cours:
            return

        if not self.moteur.blocs_a_traiter(
            CIBLE_NON_VALIDES
        ):
            QMessageBox.information(
                self,
                "Rien à traiter",
                "Tous les blocs sont validés."
            )
            return

        self.passe_en_cours = True

        self.annulation_passe = type(
            "A", (), {"demandee": False}
        )()

        self.traiter_button.setEnabled(False)
        self.annuler_button.setVisible(True)

        self.barre_etat.setText(
            "Traitement en cours… "
            "(l'annulation conserve tout ce qui est "
            "déjà produit)"
        )

        self.thread_passe = QThread(self)
        self.worker_passe = ReformulationWorker(
            self.moteur,
            self.annulation_passe,
            CIBLE_NON_VALIDES
        )

        self.worker_passe.moveToThread(
            self.thread_passe
        )

        self.thread_passe.started.connect(
            self.worker_passe.run
        )

        self.worker_passe.progression.connect(
            self.sur_progression_passe
        )

        self.worker_passe.bloc_traite.connect(
            self.sur_bloc_traite
        )

        self.worker_passe.terminee.connect(
            self.sur_passe_terminee
        )

        self.worker_passe.terminee.connect(
            self.thread_passe.quit
        )

        self.worker_passe.erreur.connect(
            self.sur_passe_terminee
        )

        self.thread_passe.start()

    def annuler_traitement(self):
        """
        B2 : l'annulation arrête proprement à la fin
        de l'appel en cours ; tout résultat déjà
        produit est conservé.
        """

        if self.annulation_passe is not None:
            self.annulation_passe.demandee = True

        self.annuler_button.setEnabled(False)
        self.barre_etat.setText(
            "Interruption demandée — fin de l'appel "
            "en cours…"
        )

    def sur_progression_passe(
        self,
        traites: int,
        total: int
    ):
        """
        La progression et la barre d'état restent
        visibles même avec un filtre locuteur actif
        (règle 6).
        """

        self.barre_etat.setText(
            f"Traitement : {traites} / {total} blocs…"
        )

    def sur_bloc_traite(self, fid: int):

        ligne = self.lignes.get(fid)

        if ligne is not None:
            ligne.consultation = None
            ligne.non_enregistre = False
            self.rafraichir_ligne(fid)

        self.maj_barre_etat()

    def sur_passe_terminee(self, resultat):
        """
        Fin de passe : affichage du coût réel (B1 :
        fait office de confirmation de la passe
        suivante).
        """

        self.passe_en_cours = False

        self.traiter_button.setEnabled(True)
        self.annuler_button.setVisible(False)
        self.annuler_button.setEnabled(True)

        self.thread_passe = None
        self.worker_passe = None

        for fid in self.lignes:
            self.rafraichir_ligne(fid)

        self.maj_barre_etat()

        cout = resultat.cout_total
        duree = resultat.duree_ms

        if resultat.statut == "terminee":
            message = (
                f"Passe terminée : "
                f"{resultat.nb_traites} bloc(s) traité(s).\n\n"
                f"Coût réel : {cout:.3f} €\n"
                f"Durée : {duree / 1000:.0f} s"
            )

            QMessageBox.information(
                self,
                "Traitement terminé",
                message
            )

        elif resultat.statut == "annulee":
            QMessageBox.information(
                self,
                "Passe interrompue",
                (
                    f"{resultat.message}\n\n"
                    "Les résultats produits sont "
                    "conservés ; relancer le traitement "
                    "reprend au premier bloc sans "
                    "résultat."
                )
            )

        else:
            QMessageBox.critical(
                self,
                "Erreur pendant la passe",
                (
                    f"La passe s'est arrêtée : "
                    f"{resultat.message}\n\n"
                    "Les résultats déjà produits sont "
                    "conservés ; la reprise sautera les "
                    "blocs traités."
                )
            )

    def afficher_couts_estimes(self):
        """
        Estimation du coût de la passe aux prix
        courants du catalogue (B1).
        """

        try:
            estimation = self.moteur.estimer_passe(
                CIBLE_NON_VALIDES
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Estimation impossible",
                str(e)
            )
            return

        QMessageBox.information(
            self,
            "Coûts estimés",
            (
                f"Blocs à traiter : "
                f"{estimation['nb_blocs']}\n"
                f"Modèle : {estimation['modele']}\n"
                f"Tokens entrée estimés : "
                f"{estimation['tokens_in_estimes']}\n"
                f"Tokens sortie estimés : "
                f"{estimation['tokens_out_estimes']}\n\n"
                f"Coût estimé : "
                f"{estimation['cout_estime']:.3f} €"
            )
        )

    #
    # ==================================================
    # Contrôle qualité (indicateur discret, spec §4).
    # ==================================================
    #

    def afficher_controles(self, fid: int):

        ligne = self.lignes.get(fid)

        if ligne is None:
            return

        resultat = self.derniere_version(fid)

        if resultat is None:
            QToolTip.showText(
                ligne.pastille.mapToGlobal(
                    ligne.pastille.rect().bottomLeft()
                ),
                "Aucun résultat à contrôler.",
            )
            return

        controles = controles_bloc(
            ligne.bloc.source,
            ligne.cellule_reformee.toPlainText(),
            self.etude.parametres.controle_qualite
        )

        message = (
            controles["longueur"]["message"]
            + "\n"
            + controles["message_interdits"]
        )

        QToolTip.showText(
            ligne.pastille.mapToGlobal(
                ligne.pastille.rect().bottomLeft()
            ),
            message
        )

    #
    # ==================================================
    # Locuteurs (API de filtrage conservée,
    # spec correctifs §2.3 — retirée de l'UI,
    # prête à être rebranchée sur un menu
    # « Filtrer par locuteur… » de la barre
    # supérieure).
    # ==================================================
    #

    def selectionner_locuteur(self, locuteur: str):
        """
        Filtre par locuteur (API conservée — plus
        exposée dans l'UI depuis P16-bis) ; le
        traitement en cours et la barre d'état ne
        sont jamais masqués (règle 6).
        """

        if self.locuteur_selectionne == locuteur:
            self.locuteur_selectionne = None
        else:
            self.locuteur_selectionne = locuteur

        for ligne in self.lignes.values():
            self.appliquer_filtrage(ligne)

    def appliquer_filtrage(self, ligne: LigneBloc):
        """
        Un bloc fusionné multi-locuteurs apparaît
        chez chacun de ses locuteurs.
        """

        if self.locuteur_selectionne is None:
            visible = True
        else:
            visible = (
                self.locuteur_selectionne
                in ligne.bloc.locuteurs
            )

        rangée = self.rangees.get(ligne.bloc.fid)

        if rangée is not None:
            self.table.setRowHidden(rangée, not visible)

    def ligne_visible(self, fid: int) -> bool:
        """
        Visibilité d'une ligne de bloc (API de
        filtrage conservée).
        """

        rangée = self.rangees.get(fid)

        if rangée is None:
            return False

        return not self.table.isRowHidden(rangée)

    #
    # ==================================================
    # Audio et timeline (composant v1, spec §3).
    # ==================================================
    #

    def brancher_audio(self):
        """
        Charge l'audio du projet v1 et branche le
        surlignage du mot lu (E1.3) et la timeline.
        """

        if self.projet_v1 is None:
            self.jouer_button.setEnabled(False)
            return

        if not self.projet_v1.audio_file:

            self.jouer_button.setEnabled(False)
            return

        chemin_audio = Path(self.projet_v1.audio_file)

        if not chemin_audio.exists():
            self.jouer_button.setEnabled(False)
            return

        self.playback.load_file(str(chemin_audio))

        self.playback.position_changed.connect(
            self.sur_position_audio
        )

        self.timeline.seek_requested.connect(
            self.playback.set_position
        )

        self.timeline.block_clicked.connect(
            self.sur_bloc_timeline_clic
        )

    def jouer_audio_si_charge(self):

        if self.projet_v1 is None:
            return

        if not self.projet_v1.audio_file:
            return

        if not Path(self.projet_v1.audio_file).exists():
            return

        self.playback.play()
        self.jouer_button.setText("⏸ Pause")

    def basculer_lecture(self):

        if self.playback is None:
            return

        if self.jouer_button.text() == "▶ Audio":
            self.playback.play()
            self.jouer_button.setText("⏸ Pause")
        else:
            self.playback.pause()
            self.jouer_button.setText("▶ Audio")

    def sur_position_audio(self, position: float):
        """
        Surligne le mot lu dans la cellule brute et
        surbrille le bloc joué (E1.3, spec §3).
        """

        for fid, ligne in self.lignes.items():

            debut = lire_timecode(
                ligne.bloc.positions.debut
            )

            fin = lire_timecode(
                ligne.bloc.positions.fin
            )

            jouee = debut <= position < fin

            ligne.cellule_brute.setStyleSheet(
                "border-left: 3px solid "
                + (COULEUR_MODIFIABLE if jouee else "transparent")
                + ";"
            )

            if not jouee:
                ligne.surligner_mot(None)
                continue

            index = None

            for i, mot in enumerate(ligne.mots):
                if (
                    mot.start is not None
                    and mot.start <= position
                    and (
                        mot.end is None
                        or position < mot.end
                        or mot.end <= position
                    )
                ):
                    index = i
                    if (
                        mot.end is None
                        or position < mot.end
                    ):
                        break

            ligne.surligner_mot(index)

    def sur_bloc_timeline_clic(self, block_id: int):
        """
        La timeline v1 signale un bloc par son id
        v1 : positionner l'audio au début du bloc.
        """

        if self.projet_v1 is None:
            return

        bloc_v1 = self.projet_v1.get_block_by_id(
            block_id
        )

        if bloc_v1 is None:
            return

        mots = self.projet_v1.get_block_items(bloc_v1)

        if mots:

            premier = mots[0]

            if premier.start is not None:
                self.playback.set_position(
                    float(premier.start)
                )
                return

        debut = min(
            mot.start
            for mot in mots
            if mot.start is not None
        ) if mots else 0.0

        self.playback.set_position(float(debut))

    #
    # ==================================================
    # Divers.
    # ==================================================
    #

    def changer_taille(self, delta: int):
        """
        A+ / A− : agit simultanément sur les deux
        colonnes ; la taille est mémorisée dans les
        réglages (spec correctifs §5) et les
        hauteurs de lignes suivent le nouvel
        étalonnement du texte.
        """

        self.taille_texte = max(
            TAILLE_TEXTE_MIN,
            min(TAILLE_TEXTE_MAX, self.taille_texte + delta)
        )

        for ligne in self.lignes.values():
            ligne.appliquer_taille(self.taille_texte)

        for fid in self.lignes:
            self._ajuster_hauteur_ligne(fid)

        self._enregistrer_prefs()

    def _enregistrer_prefs(self):
        """
        Mémorise la taille du texte et les largeurs
        de colonnes (spec correctifs §5.2 et règle
        d'invariance 4 : conservées après
        fermeture/réouverture).
        """

        self.settings.set_reformulation_prefs({
            "taille_texte": self.taille_texte,
            "largeur_locuteurs": (
                self.table.columnWidth(0)
            ),
            "largeur_brute": (
                self.table.columnWidth(1)
            ),
            "largeur_pastilles": (
                self.table.columnWidth(3)
            ),
        })

    def closeEvent(self, event):

        self._enregistrer_prefs()

        super().closeEvent(event)

    def sauvegarder_etude(self):

        from services.etude_io import (
            sauvegarder_etude
        )

        sauvegarder_etude(self.etude)

    def ouvrir_log(self):
        """
        Page Log des opérations (spec §8) : lecture
        seule, copie possible, rafraîchie à
        l'ouverture.
        """

        from ui.log_window import LogWindow

        dialogue = LogWindow(
            self.etude.journal,
            parent=self
        )

        dialogue.exec()

    def retour_accueil(self):

        self.sauvegarder_etude()

        self.playback.stop()
        self.playback.unload()

        from ui.etude_window import EtudeWindow

        self.etude_window = EtudeWindow(self.etude.dossier)

        self.etude_window.show()

        self.close()
