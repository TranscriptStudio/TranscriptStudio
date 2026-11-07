from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,

    QLabel,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
    QInputDialog,
    QMenu,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import (
    QThread,
    Qt,
    QSize,
    Signal,
)
from PySide6.QtGui import (
    QPixmap,
    QFont,
    QFontDatabase,
    QIcon,
    QPalette,
    QColor,
)

from pathlib import Path

import functools

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
from ui.stepper import StepperBar


class TuileAccueil(QWidget):
    """
    Grande carte du hub (P18.6-bis, spec correctifs
    §1 et §22) : icône, titre exact, paragraphe
    descriptif, coins arrondis, marge intérieure
    généreuse — le clic sur la tuile déclenche
    l'action.

    §22 : CONTOUR VISIBLE (1 px, gris plus clair
    que le fond de page — la tuile se détache du
    fond, jamais ne s'y fond) et EFFET DE SURVOL
    identique aux maquettes : élévation ~2 px,
    contour passant au bleu d'accent (#3b9eff — série 5, spec 30f §23),
    OMBRE PORTÉE vers le bas DISCRÈTE (4 % d'opacité,
    flou doux 12 px — série 7, retour David point 2) —
    l'effet est PROGRESSIF (contour, élévation et
    ombre animés ensemble, ~120 ms — spec 30f
    §22/invariant 10), retour immédiat en sortie
    de survol, curseur main.

    Carte moins large que la rangée : rapport
    3:2 (~300 × 200 px), la rangée des trois
    cartes reste centrée.

    Icônes : illustrations PNG fournies par
    David (resources/icons/, affichées telles
    quelles, centrées, à l'échelle homothétique).
    """

    clique = Signal()

    ELEVATION_SURVOL = 2
    DUREE_SURVOL_MS = 120

    #
    # P18.6-bis série 7 (retour David, point 2) :
    # ombre de survol BEAUCOUP plus subtile
    # (naguère flou 24 px, décalée de 8 px, 8 %
    # d'opacité — halo large et trop visible) :
    # flou doux 12 px, décalée de 3 px, 4 %.
    #
    OPACITE_OMBRE_SURVOL = 0.04
    RAYON_OMBRE_SURVOL = 12
    DECALAGE_OMBRE_SURVOL = 3

    LARGEUR_CARTE = 300
    HAUTEUR_CARTE = 200

    #
    # Zone d'icône des tuiles (illustrations PNG
    # fournies par l'utilisateur, 2026-11-07) :
    # hauteur FIXE identique pour les trois tuiles
    # (alignement vertical des libellés conservé),
    # largeur = largeur disponible de la carte ;
    # chaque PNG est mis à l'échelle HOMOTHÉTIQUE
    # (KeepAspectRatio, jamais de rognage) et CENTRÉ
    # horizontalement.
    #
    HAUTEUR_ZONE_ICONE = 64

    def __init__(
        self,
        titre: str,
        description: str,
        icone=None,
        parent=None
    ):
        super().__init__(parent)

        self.setObjectName("tuile_hub")

        self.titre = titre

        #
        # Métriques (§22 + retour David) : carte
        # moins large — rapport 3:2 (300 × 200),
        # coins arrondis (12 px), marge intérieure
        # généreuse (22/20/18), icône 34 px,
        # titre 16 px, description discrète.
        #
        self.setFixedSize(
            self.LARGEUR_CARTE,
            self.HAUTEUR_CARTE
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        #
        # CRITIQUE : une sous-classe de QWidget
        # n'affiche PAS sa feuille de style (fond,
        # bordure, coins arrondis) sans cet
        # attribut — sans lui, la carte est
        # invisible (aucun fond, aucun contour),
        # quel que soit le style écrit.
        #
        self.setAttribute(
            Qt.WidgetAttribute
            .WA_StyledBackground,
            True
        )

        #
        # Ombre portée du survol (vers le bas,
        # 8 % d'opacité) — alpha animé.
        #
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import (
            QGraphicsDropShadowEffect,
        )

        self._ombre = (
            QGraphicsDropShadowEffect(self)
        )
        self._ombre.setBlurRadius(
            self.RAYON_OMBRE_SURVOL
        )
        self._ombre.setOffset(
            0,
            self.DECALAGE_OMBRE_SURVOL,
        )
        self._ombre.setColor(
            QColor(0, 0, 0, 0)
        )

        self.setGraphicsEffect(self._ombre)

        self._appliquer_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 22, 20, 18)
        layout.setSpacing(0)

        if icone is not None:

            icone_label = QLabel()

            #
            # PNG fourni par l'utilisateur : affiché
            # TEL QUEL (pas de teinte par thème — ce
            # n'est pas un SVG teinté), centré
            # horizontalement, à l'échelle
            # homothétique dans la zone d'icône.
            #
            icone_label.setAlignment(
                Qt.AlignmentFlag.AlignHCenter
            )

            pixmap = QPixmap(str(icone))

            pixmap = pixmap.scaled(
                self.LARGEUR_CARTE - 40,
                self.HAUTEUR_ZONE_ICONE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            icone_label.setPixmap(pixmap)

            # Hauteur de zone fixe : les libellés des
            # trois tuiles restent alignés verticalement
            # quel que soit le ratio du PNG.
            icone_label.setFixedHeight(
                self.HAUTEUR_ZONE_ICONE
            )

            layout.addWidget(
                icone_label,
                alignment=(
                    Qt.AlignmentFlag.AlignHCenter
                ),
            )
            layout.addSpacing(10)

        titre_label = QLabel(titre)
        titre_label.setStyleSheet(
            "font-size: 16px; font-weight: 600;"
            "border: none;"
        )

        layout.addWidget(titre_label)
        layout.addSpacing(6)

        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setStyleSheet(
            "font-size: 12px; color: "
            + self._couleur_description()
            + ";"
            "border: none;"
        )

        layout.addWidget(
            description_label,
            stretch=1
        )

        layout.addStretch()

        #
        # Animation d'élévation au survol (~120 ms),
        # retour immédiat en sortie.
        #
        self._position_base = None
        self._animation = None

    def _couleur_description(self) -> str:
        """
        Couleur du paragraphe descriptif (maquette :
        #a6a7ae en thème sombre).
        """

        from services.theme_manager import (
            couleurs_tuiles,
            est_sombre,
        )

        return couleurs_tuiles(
            est_sombre(self)
        )["description"]

    def _appliquer_style(
        self,
        progression: float = 0.0
    ):
        """
        Contour visible + survol PROGRESSIF (retour
        David) : bord 1 px gris plus clair que le
        fond, fond de tuile légèrement plus clair
        que le fond de page, coins arrondis 12 px.
        Au survol, le contour glisse vers le bleu
        d'accent au fil de l'animation (plus de
        bascule :hover instantanée).
        """

        from services.theme_manager import (
            BORD_BLEU_ACCENT,
            couleurs_tuiles,
            est_sombre,
            melanger_couleurs,
        )

        self._couleurs_base = couleurs_tuiles(
            est_sombre(self)
        )

        bord = melanger_couleurs(
            self._couleurs_base["bord"],
            BORD_BLEU_ACCENT,
            progression
        )

        self.setStyleSheet(
            "QWidget#tuile_hub {"
            "border: 1px solid "
            + bord
            + ";"
            "border-radius: 12px;"
            "background-color: "
            + self._couleurs_base["fond"]
            + ";"
            "}"
            # Les enfants (icône, titre, description)
            # restent TRANSPARENTS : sans cette règle,
            # la feuille qdarktheme les repeint de la
            # couleur du thème et masque le fond de la
            # carte.
            "QWidget#tuile_hub QLabel {"
            "background-color: transparent;"
            "border: none;"
            "}"
        )

    def enterEvent(self, event):
        """
        Entrée de survol : élévation, contour bleu
        et ombre portée montent ENSEMBLE, de façon
        PROGRESSIVE (~200 ms).
        """

        from PySide6.QtCore import (
            QVariantAnimation,
        )

        self._position_base = self.pos()

        if self._animation is not None:
            self._animation.stop()

        self._animation = QVariantAnimation(
            self
        )

        self._animation.setDuration(
            self.DUREE_SURVOL_MS
        )

        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)

        self._animation.valueChanged.connect(
            self._appliquer_progression
        )

        self._animation.start()

        super().enterEvent(event)

    def _appliquer_progression(
        self,
        progression: float
    ):
        """
        Une étape de l'animation de survol :
        élévation (2 px), contour glissant vers le
        bleu d'accent, ombre vers le bas (8 %
        d'opacité au terme).
        """

        from PySide6.QtGui import QColor

        if self._position_base is None:
            return

        #
        # Élévation progressive.
        #
        self.move(
            self._position_base.x(),
            self._position_base.y() - (
                self.ELEVATION_SURVOL
                * progression
            ),
        )

        #
        # Contour progressif (gris -> bleu d'accent).
        #
        self._appliquer_style(progression)

        #
        # Ombre portée progressive (8 % à terme).
        #
        alpha = int(
            255
            * self.OPACITE_OMBRE_SURVOL
            * progression
        )

        self._ombre.setColor(
            QColor(0, 0, 0, alpha)
        )

    def leaveEvent(self, event):
        """
        Sortie de survol : retour IMMÉDIAT (pas
        d'animation inverse — spec §22) : carte
        reposée, contour gris, ombre effacée.
        """

        if self._animation is not None:
            self._animation.stop()
            self._animation = None

        if self._position_base is not None:
            self.move(self._position_base)
            self._position_base = None

        from PySide6.QtGui import QColor

        self._appliquer_style(0.0)
        self._ombre.setColor(QColor(0, 0, 0, 0))

        super().leaveEvent(event)

    def mousePressEvent(self, event):

        self.clique.emit()

        super().mousePressEvent(event)


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

        # Étape en cours de chaque réunion récente
        # (chemin -> étape) — le clic gauche sur une
        # tuile ouvre la réunion à SON étape en
        # cours (retour David, point 3c).
        self._etapes_recentes = {}

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
                120,
                120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.logo_label = icon_label

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
            "Prétraitement audio, transcription et "
            "reformulation assistés"
        )
        self.version_label = QLabel("Version 2.0")

        title_layout.addWidget(self.title_label)
        title_layout.addSpacing(4)
        title_layout.addWidget(self.subtitle_label)
        title_layout.addSpacing(4)
        title_layout.addWidget(self.version_label)

        header_layout.addWidget(
            icon_label,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        #
        # Pastilles de services sur PLAQUE « métal
        # brossé » (spec 30f §25a), placée à gauche
        # des boutons ⚙/? : seul le POINT est
        # coloré (vert ok / rouge ko / gris off), le
        # texte reste en couleur normale. FFmpeg et
        # Bible n'y figurent pas (diagnostic
        # uniquement pour FFmpeg ; la version de
        # Bible est propre à chaque étude).
        #
        from services.theme_manager import (
            BORD_BLEU_ACCENT,
        )

        self.plaque_services = QFrame()
        self.plaque_services.setObjectName(
            "plaque_services"
        )

        # P18.6-bis série 7 (retour David, point 5) :
        # plaque sur UNE SEULE LIGNE — les deux
        # services côte à côte — et hauteur
        # HOMOGÈNE avec les boutons ⚙/? voisins
        # (34 px, verticalement centrée).
        self.plaque_services.setFixedHeight(34)

        plaque_layout = QHBoxLayout(self.plaque_services)
        plaque_layout.setContentsMargins(12, 0, 12, 0)
        plaque_layout.setSpacing(16)

        def ligne_service(texte):
            """
            Un service de la plaque : un GROUPE
            (point + libellé) qui porte sa propre
            INFO-BULLE — le survol du libellé ou du
            point montre l'état du service (retour
            David, point 2).

            Le libellé est posé par QFont (et non
            par la feuille de style) : un
            ``font-size`` de feuille de style ne se
            reflète pas dans le sizeHint, qui
            réclamait alors le double de la largeur
            réellement affichée (plaque démesurée).
            """

            groupe = QWidget()
            contenu = QHBoxLayout(groupe)
            contenu.setContentsMargins(0, 0, 0, 0)
            contenu.setSpacing(7)

            point = QLabel()
            point.setFixedSize(9, 9)
            point.setStyleSheet(
                "border-radius: 4px;"
                "background-color: #8a8b92;"
            )

            libelle = QLabel(texte)

            police = QFont(self.font())
            police.setPixelSize(11)
            libelle.setFont(police)

            contenu.addWidget(point)
            contenu.addWidget(libelle)

            plaque_layout.addWidget(groupe)

            return groupe, point

        self.ligne_api, self.api_pastille = (
            ligne_service("Service de transcription")
        )

        self.ligne_llm, self.llm_pastille = (
            ligne_service("Service IA")
        )

        self._appliquer_style_plaque()

        #
        # Libellés d'état complets conservés
        # (masqués) — ils portent le détail
        # « configuré / non configuré » des tests
        # P16-bis et servent d'info-bulles.
        #
        self.api_status_label = QLabel("")
        self.api_status_label.setStyleSheet("font-size: 12px; color: #666666;")
        self.api_status_label.setVisible(False)

        self.llm_status_label = QLabel("")
        self.llm_status_label.setStyleSheet("font-size: 12px; color: #666666;")
        self.llm_status_label.setVisible(False)

        header_layout.addWidget(
            self.plaque_services,
            alignment=(
                Qt.AlignmentFlag.AlignVCenter
            ),
        )

        #
        # Boutons du bandeau (§25b) : UNE SEULE
        # ICÔNE chacun, pas de texte ; survol au
        # contour d'accent (§23).
        #
        style_bouton = (
            "QPushButton {"
            "border: 1px solid transparent;"
            "border-radius: 8px;"
            "background: transparent;"
            "}"
            "QPushButton:hover {"
            "border: 1px solid "
            + BORD_BLEU_ACCENT
            + ";"
            "}"
        )

        self.settings_button = QPushButton()
        self.settings_button.setIcon(
            QIcon(str(resource_path("icons/settings.svg")))
        )
        self.settings_button.setToolTip("Configurer Transcript Studio")

        self.help_button = QPushButton()
        self.help_button.setIcon(
            QIcon(str(resource_path("icons/info-square-rounded.svg")))
        )
        self.help_button.setToolTip("Ouvrir le manuel utilisateur")

        for button in (
            self.settings_button,
            self.help_button,
        ):
            button.setFixedSize(38, 34)
            button.setIconSize(QSize(19, 19))
            button.setStyleSheet(style_bouton)

        header_layout.addWidget(self.settings_button)
        header_layout.addWidget(self.help_button)

        layout.addWidget(self.bandeau)

        #
        # Trois GRANDES tuiles (spec correctifs §1) :
        # icône, titre exact, paragraphe descriptif —
        # le clic sur la tuile déclenche l'action.
        # Icônes : illustrations PNG de David
        # (resources/icons/).
        #
        self.tuiles_layout = QHBoxLayout()
        tuiles_layout = self.tuiles_layout
        tuiles_layout.setContentsMargins(0, 0, 0, 0)
        tuiles_layout.setSpacing(12)

        self.tuile_nouvelle = TuileAccueil(
            "Nouvelle transcription",
            "Prétraiter un audio (optionnel), lancer "
            "la transcription et éventuellement "
            "poursuivre le processus (reformulation, "
            "etc.).",
            icone=resource_path(
                "resources/icons/microphone.png"
            ),
        )

        self.tuile_reprendre = TuileAccueil(
            "Reprendre une réunion",
            "Reprendre le travail où vous l'avez "
            "laissé : correction de transcription, "
            "reformulation, résumé, etc.",
            icone=resource_path(
                "resources/icons/dossier.png"
            ),
        )

        self.tuile_etudes = TuileAccueil(
            "Études",
            "Créer une étude, ouvrir et gérer une "
            "étude existante. Une étude est un "
            "regroupement de réunions ayant pour "
            "objet un thème spécifique.",
            icone=resource_path(
                "resources/icons/livre_étude.png"
            ),
        )

        #
        # Retour David : cartes MOINS LARGES —
        # rapport 3:2, la rangée des trois cartes
        # reste centrée (marges élastiques).
        #
        tuiles_layout.addStretch()

        for tuile in (
            self.tuile_nouvelle,
            self.tuile_reprendre,
            self.tuile_etudes,
        ):
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
        # Connexions des tuiles.
        #
        self.tuile_nouvelle.clique.connect(
            self.new_transcription
        )
        self.tuile_reprendre.clique.connect(
            self.open_project
        )
        self.tuile_etudes.clique.connect(
            self.ouvrir_menu_etudes
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

        #
        # §22 : les tuiles se détachent du fond de
        # page — en thème sombre, fond de page des
        # maquettes (#1e1f24).
        #
        self._appliquer_fond_page()

        # Dernieres reunions.
        self.refresh_dernieres_reunions()

        self._ui_construite = True

    def _appliquer_fond_page(self):
        """
        Fond de page UNIQUE hors tuiles, dans les DEUX
        thèmes (retour David, points 1, 4 et 5) :

        - sombre : fond des maquettes #1e1f24 sur la
          fenêtre ET sur les zones de contenu
          non-tuile (qdarktheme peint SINON tout
          QWidget et tout QLabel en #202124 —
          c'est la « légère différence de couleur »
          du bandeau supérieur et de la ligne
          « Dernières réunions » — série 7,
          retour David point 1) ;
        - clair : gris élégant de Windows #f3f3f3 —
          plus aucun blanc pur sur le hub.

        Les contours et fonds propres des tuiles et
        de la plaque des services sont posés par
        leurs feuilles de style respectives : ils
        priment sur ces règles de transparence.
        """

        from services.theme_manager import (
            FOND_PAGE_CLAIR,
            FOND_PAGE_SOMBRE,
            est_sombre,
        )

        fond = (
            FOND_PAGE_SOMBRE
            if est_sombre(self)
            else FOND_PAGE_CLAIR
        )

        self.setAttribute(
            Qt.WidgetAttribute
            .WA_StyledBackground,
            True
        )
        self.setStyleSheet(
            "HomeWindow {"
            "background-color: "
            + fond
            + ";"
            "}"
            # Zone non-tuile DIRECTE (le bandeau
            # supérieur notamment) : transparente.
            "HomeWindow > QWidget {"
            "background: transparent;"
            "border: none;"
            "}"
            # Tout label du hub : transparent (le
            # titre « Dernières réunions »
            # notamment) — les labels des tuiles
            # et du menu Études portent leurs
            # propres feuilles de style.
            "HomeWindow QLabel {"
            "background: transparent;"
            "border: none;"
            "}"
            "QScrollArea {"
            "background: transparent;"
            "border: none;"
            "}"
            "QScrollArea > QWidget > QWidget {"
            "background: transparent;"
            "border: none;"
            "}"
        )

    def _appliquer_style_plaque(self):
        """
        Style de la plaque des services selon le
        thème : « métal brossé » des maquettes en
        sombre, plaque claire discrète en clair
        (P18.6-bis série 6 — la plaque sombre ne
        s'affiche PLUS en thème clair).
        """

        from services.theme_manager import (
            couleurs_plaque_services,
            est_sombre,
        )

        couleurs = couleurs_plaque_services(
            est_sombre(self)
        )

        self.plaque_services.setStyleSheet(
            "QFrame#plaque_services {"
            "background-color: qlineargradient("
            "x1:0, y1:0, x2:0, y2:1,"
            " stop:0 "
            + couleurs["degrade_haut"]
            + ", stop:1 "
            + couleurs["degrade_bas"]
            + ");"
            "border: 1px solid "
            + couleurs["bord"]
            + ";"
            "border-radius: 8px;"
            "}"
            "QFrame#plaque_services QLabel {"
            "background: transparent;"
            "border: none;"
            "}"
            "QFrame#plaque_services QWidget {"
            "background: transparent;"
            "}"
        )

        for ligne in (
            self.ligne_api,
            self.ligne_llm,
        ):
            for libelle in ligne.findChildren(QLabel):
                if libelle.text():
                    libelle.setStyleSheet(
                        "color: "
                        + couleurs["texte"]
                        + ";"
                    )

    #
    # ==================================================
    # Tuile « Études » : menu déroulant (P18.6-bis
    # série 4, spec correctifs §21 — la page
    # intermédiaire de choix est supprimée).
    # ==================================================
    #

    def ouvrir_menu_etudes(self):
        """
        Tuile « Études » : PANNEAU DÉROULANT ancré
        sous la tuile (maquette P18.6-bis série 4)
        — en-tête « Vos études », une ligne par
        étude (pastille de couleur, nom, thème ·
        date de modification, badge « N réunions »),
        séparateur, « ＋ Nouvelle étude… » et
        « Ouvrir depuis un dossier… ». Choisir une
        étude ouvre DIRECTEMENT la page Étude ;
        Échap ou clic extérieur referment le
        panneau (Qt.Popup + touche Échap).
        """

        from ui.menu_etudes import MenuEtudes

        self.menu_etudes = MenuEtudes(
            self.settings,
            parent=self
        )

        self.menu_etudes.etude_choisie.connect(
            self.ouvrir_etude
        )

        self.menu_etudes.nouvelle_etude.connect(
            self.creer_etude_ui
        )

        self.menu_etudes.ouvrir_dossier.connect(
            self.ouvrir_etude_dialogue
        )

        self.menu_etudes.ouvrir_sous(
            self.tuile_etudes
        )

    def ouvrir_etude(self, dossier):
        """
        Ouvre la page Étude DIRECTEMENT (menu de la
        tuile « Études ») via la pile de navigation
        (repli : fenêtre autonome pour les tests et
        le lancement direct).
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
        s'ouvre), ouverture DIRECTE de la page
        Étude.
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
                    "« ＋ Nouvelle étude »."
                )
            )
            return

        self.ouvrir_etude(dossier)

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

        self._etapes_recentes = {}

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
        Tuile-rangée de réunion (spec 30f §26) :
        CLIQUABLE, sans bouton « Ouvrir » —
        marque carrée d'accent, titre, étude,
        stepper compact (ou mention si non
        transcrite), coût à droite ; UNE ligne,
        DEUX lignes en fenêtre étroite. Réunion
        autonome : AUCUN lien de rattachement
        (série 7, retour David point 3 — le menu
        contextuel s'en charge), la rangée garde
        la hauteur des autres (steppers alignés,
        point 4).

        Retourne None si le projet est illisible
        (la liste des récents est déjà nettoyée par
        les réglages pour les fichiers disparus).
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
        from ui.tuiles import TuileReunion

        rattachement = rattachement_de(
            chemin,
            etudes
        )

        etude_ouverte = None
        nom_reunion = None
        texte_etude = None
        cout = 0.0

        if rattachement is not None:

            dossier, nom_reunion = rattachement

            try:

                etude_ouverte = ouvrir_etude(dossier)

                titre_etude = (
                    etude_ouverte.etude.titre
                )

                texte_etude = (
                    f"Étude « {titre_etude} »"
                )

                cout = cout_reunion(
                    etude_ouverte,
                    nom_reunion
                )

            except Exception:
                etude_ouverte = None

        titre = Path(chemin).parent.name

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

        #
        # Étape en cours (retour David, point 3c) :
        # le clic GAUCHE sur la tuile ouvre la
        # réunion directement à l'étape en cours —
        # la première pastille bleue ; la première
        # étape non terminée s'il n'y en a pas.
        #
        from services.avancement import (
            etape_courante,
        )

        etape = (
            etape_courante(etats)
            if etats is not None
            else None
        )

        if etats is None:

            #
            # P18.6-bis série 6 (SPEC_NAVIGATION_
            # MODIFS_2026-10-31a §29) : le hub
            # n'affiche NI stepper NI MENTION pour
            # une réunion non transcrite (la page
            # Étude conserve sa mention discrète).
            #
            fabrique_stepper = None

        else:

            def fabrique_stepper():
                stepper = StepperBar(
                    cliquable=False,
                    compact=True
                )
                stepper.definir_etats(etats)
                return stepper

        cout_libelle = (
            f"Coût : {cout:.4f} $"
            if cout
            else "Coût : —"
        )

        tuile = TuileReunion(
            str(chemin),
            titre,
            texte_etude,
            fabrique_stepper=fabrique_stepper,
            cout=cout_libelle,
        )

        tuile.setToolTip(str(chemin))

        tuile.rattachee = (
            texte_etude is not None
        )

        tuile.etape_courante = etape

        self._etapes_recentes[str(chemin)] = etape

        tuile.ouvrir_demandee.connect(
            self.ouvrir_reunion_depuis_hub
        )

        tuile.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        # functools.partial et non une lambda :
        # les signaux connectés à des lambdas
        # provoquent un segfault Nuitka/PySide6
        # (P12).
        tuile.customContextMenuRequested.connect(
            functools.partial(
                self.afficher_menu_mini_tuile,
                tuile,
                str(chemin),
            )
        )

        return tuile

    def ouvrir_reunion_depuis_hub(self, chemin):
        """
        Ouvre la page Réunion d'une mini-tuile (via la
        pile de navigation si la destination existe,
        sinon repli sur la page Correction — lancement
        autonome et tests).

        Retour David, point 3c : la réunion s'ouvre
        à SON ÉTAPE EN COURS (première pastille
        bleue, première étape non terminée sinon) —
        le stepper de la tuile n'est plus un lien
        vers chaque étape.
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

        etape = self._etapes_recentes.get(
            str(chemin)
        )

        navigation = getattr(self, "navigation", None)

        if (
            navigation is not None
            and hasattr(
                navigation,
                "ouvrir_reunion"
            )
        ):
            navigation.ouvrir_reunion(
                projet,
                etape=etape
            )
            return

        self.ouvrir_correction(projet)

    def rattacher_reunion(self, chemin):
        """
        Rattachement d'une réunion autonome à une
        étude (spec §2.4) : proposé par le menu
        contextuel de la tuile (clic droit — série 7,
        retour David point 3 : plus de lien dans la
        rangée), disponible à tout moment, dès le
        prétraitement.
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
        Menu contextuel (clic DROIT) d'une tuile de
        réunion — retour David, point 3d :

        - ouvrir la réunion à l'étape en cours ;
        - rattacher la réunion à une étude
          existante — option ABSENTE (et non
          grisée) si la réunion appartient déjà
          à une étude ;
        - retirer de la liste des réunions
          récentes (jamais du disque).
        """

        menu = self._construire_menu_mini_tuile(
            cadre,
            chemin
        )

        menu.exec(
            cadre.mapToGlobal(pos)
        )

    def _construire_menu_mini_tuile(
        self,
        cadre,
        chemin
    ):
        """
        Construit le menu contextuel d'une tuile de
        réunion (séparé de l'affichage pour être
        testable sans exécuter le menu).
        """

        menu = QMenu(self)

        ouvrir_action = menu.addAction(
            "Ouvrir la réunion à l'étape en cours"
        )
        ouvrir_action.triggered.connect(
            functools.partial(
                self.ouvrir_reunion_depuis_hub,
                chemin
            )
        )

        rattachee = getattr(
            cadre,
            "rattachee",
            False
        )

        if not rattachee:
            rattacher_action = menu.addAction(
                "Rattacher la réunion à une étude existante"
            )
            rattacher_action.triggered.connect(
                functools.partial(
                    self.rattacher_reunion,
                    chemin
                )
            )

        menu.addSeparator()

        retirer_action = menu.addAction(
            "Retirer de la liste des réunions récentes"
        )
        retirer_action.triggered.connect(
            functools.partial(
                self._retirer_recent,
                chemin
            )
        )

        return menu

    def _retirer_recent(self, chemin):

        self.settings.remove_recent_project(chemin)

        self.refresh_dernieres_reunions()

    def sur_changement_theme(self):
        """
        Broadcast de ThemeManager : recolore
        l'en-tête et reconstruit les dernières
        réunions (tuiles et steppers portent leurs
        couleurs à la construction).
        """

        self.update_header_colors()

    def update_header_colors(self):
        #
        # P18.6-bis série 8-ter : l'en-tête suit le
        # thème APPLIQUÉ (est_sombre), pas le seul
        # réglage configuré — l'aperçu immédiat
        # des réglages peut diverger du réglage
        # enregistré, et la palette ne reflète pas
        # qdarktheme.
        #
        from services.theme_manager import (
            est_sombre,
        )

        if est_sombre(self):
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

        # Changement de thème : la plaque des
        # services, le fond de page, les grandes
        # tuiles et les tuiles de réunion
        # reprennent immédiatement les couleurs du
        # nouveau thème (P18.6-bis série 6).
        self._appliquer_style_plaque()
        self._appliquer_fond_page()

        for tuile in (
            self.tuile_nouvelle,
            self.tuile_reprendre,
            self.tuile_etudes,
        ):
            tuile._appliquer_style(0.0)

        # Après un changement de thème (les
        # tuiles de réunion portent leurs
        # couleurs à la construction) : recon-
        # struire les dernières réunions. Pas
        # pendant la construction initiale (la
        # liste est construite en fin de build_ui).
        if getattr(self, "_ui_construite", False):
            self.refresh_dernieres_reunions()


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
        Point « Service de transcription » (ElevenLabs)
        de la plaque (spec 30f §25a) : vert si ok,
        GRIS OFF si non configuré — P18.6-bis série 6
        (SPEC_NAVIGATION_MODIFS_2026-10-31a §28) :
        le ROUGE est réservé à un échec RÉEL de
        service (erreur de connexion, clé refusée),
        jamais à une simple absence de configuration.

        Info-bulle de la LIGNE complète (retour
        David, point 2) : « clé API ElevenLabs
        configurée » — le survol fonctionne sur le
        point ET sur le libellé.
        """
        if has_transcription_api():
            self.api_status_label.setText(
                "Service de transcription : configuré"
            )
            couleur = "#3fa66c"
            bulle = (
                "clé API ElevenLabs configurée"
            )
        else:
            self.api_status_label.setText(
                "Service de transcription : non configuré"
            )
            couleur = "#8a8b92"
            bulle = (
                "clé API ElevenLabs non configurée"
            )

        self.api_pastille.setStyleSheet(
            "border-radius: 4px;"
            "background-color: "
            + couleur
            + ";"
        )

        self.ligne_api.setToolTip(bulle)

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
            couleur = "#3fa66c"

            # Liste VERTICALE des fournisseurs
            # configurés (retour David, point 2) :
            # une ligne « clé API {fournisseur}
            # configurée » par fournisseur.
            bulle = "\n".join(
                f"clé API {nom} configurée"
                for nom in noms
            )
        else:
            self.llm_status_label.setText(
                "Service de reformulation : non configuré"
            )
            couleur = "#8a8b92"
            bulle = "aucune clé API configurée"

        self.llm_pastille.setStyleSheet(
            "border-radius: 4px;"
            "background-color: "
            + couleur
            + ";"
        )

        self.ligne_llm.setToolTip(bulle)

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

        #
        # P18.6-bis (spec correctifs §19) : transcrire
        # un audio DÉJÀ PRÉTRAITÉ lors d'une session
        # précédente revient à une transcription
        # DIRECTE — le prétraitement déjà réalisé
        # n'ouvre aucune étape supplémentaire.
        #
        deja_prepare = manager.trouver_projet_prepare(
            audio_file
        )

        if deja_prepare is not None:

            audio_traite = (
                deja_prepare
                / "audio_processed.wav"
            )

            reponse = QMessageBox.question(
                self,
                "Audio déjà préparé",
                (
                    "Un prétraitement de cet audio a "
                    "déjà été finalisé :\n\n"
                    f"{deja_prepare}\n\n"
                    "Transcrire directement l'audio "
                    "préparé (sans nouveau "
                    "prétraitement) ?"
                )
            )

            if reponse != (
                QMessageBox.StandardButton.Yes
            ):
                return

            dialog = NewTranscriptionDialog(
                str(audio_traite),
                self
            )

            if not dialog.exec():
                return

            options = dialog.get_options()

            self.current_project_folder = (
                deja_prepare
            )

            self.current_audio_file = (
                audio_traite
            )

            self.start_transcription(
                audio_traite,
                options
            )

            return

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

