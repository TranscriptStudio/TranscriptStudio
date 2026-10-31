# ui/tuiles.py
"""
Comportements de tuiles partagés (P18.6-bis,
séries 4-5, spec 2026-10-30f).

- ``activer_survol_anime`` : effet de survol des
  maquettes attaché à n'importe quelle tuile —
  élévation ~2 px, contour glissant vers le bleu
  d'accent #3b9eff, OMBRE portée vers le bas à
  8 % d'opacité, transition progressive
  (~120 ms), retour immédiat en sortie,
  curseur main. S'applique aux 3 grandes cartes
  du hub ET aux tuiles-rangées (hub et page
  Étude) — invariant 10.

- ``TuileReunion`` : tuile-rangée « Dernières
  réunions » du hub (spec 30f §26) — cliquable
  SANS bouton « Ouvrir » : marque carrée
  d'accent, titre, étude, stepper compact, infos
  à droite ; UNE ligne, DEUX lignes en fenêtre
  étroite avec hauteur adaptative.
"""

from PySide6.QtCore import Qt, Signal, QVariantAnimation
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from services.theme_manager import (
    BORD_BLEU_ACCENT,
    couleurs_menu_etudes,
    couleurs_tuiles,
    est_sombre,
    melanger_couleurs,
)

ELEVATION_SURVOL = 2
DUREE_SURVOL_MS = 120

#
# P18.6-bis série 7 (retour David, point 2) :
# ombre de survol BEAUCOUP plus subtile —
# naguère blur 24 px décalée de 8 px à 8 %
# d'opacité (halo large et visible) : désormais
# flou doux de 12 px, décalé de 3 px, 4 %
# d'opacité.
#
OPACITE_OMBRE_SURVOL = 0.04
RAYON_OMBRE_SURVOL = 12
DECALAGE_OMBRE_SURVOL = 3


def activer_survol_anime(
    tuile,
    appliquer_style,
    duree=DUREE_SURVOL_MS,
    elevation=ELEVATION_SURVOL,
    opacite_ombre=OPACITE_OMBRE_SURVOL
):
    """
    Attache l'effet de survol des maquettes à une
    tuile.

    ``appliquer_style(progression)`` reconstruit
    la feuille de style de la tuile pour une
    progression donnée (0.0 = repos,
    1.0 = survol complet) — c'est là que le
    contour glisse vers l'accent.

    L'OMBRE de survol est subtile (série 7,
    retour David point 2) : flou doux 12 px,
    décalée de 3 px, 4 % d'opacité.

    La tuile doit porter WA_StyledBackground
    (posé ici) pour que sa feuille de style se
    rende.
    """

    tuile.setAttribute(
        Qt.WidgetAttribute.WA_StyledBackground,
        True
    )

    tuile.setCursor(
        Qt.CursorShape.PointingHandCursor
    )

    ombre = QGraphicsDropShadowEffect(tuile)
    ombre.setBlurRadius(RAYON_OMBRE_SURVOL)
    ombre.setOffset(0, DECALAGE_OMBRE_SURVOL)
    ombre.setColor(QColor(0, 0, 0, 0))

    tuile.setGraphicsEffect(ombre)

    etat = {
        "base": None,
        "animation": None,
    }

    def sur_progression(valeur):

        if etat["base"] is None:
            return

        tuile.move(
            etat["base"].x(),
            etat["base"].y() - elevation * valeur,
        )

        appliquer_style(valeur)

        ombre.setColor(
            QColor(
                0,
                0,
                0,
                int(255 * opacite_ombre * valeur),
            )
        )

    def sur_entree(evenement):

        if etat["animation"] is not None:
            etat["animation"].stop()

        etat["base"] = tuile.pos()

        animation = QVariantAnimation(tuile)
        animation.setDuration(duree)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.valueChanged.connect(
            sur_progression
        )

        etat["animation"] = animation

        animation.start()

    def sur_sortie(evenement):

        if etat["animation"] is not None:
            etat["animation"].stop()
            etat["animation"] = None

        if etat["base"] is not None:
            tuile.move(etat["base"])
            etat["base"] = None

        appliquer_style(0.0)

        ombre.setColor(QColor(0, 0, 0, 0))

    tuile.enterEvent = sur_entree
    tuile.leaveEvent = sur_sortie


def style_rangee(
    tuile,
    nom_objet,
    bord_base,
    fond,
    fond_survol,
    progression
) -> str:
    """
    Feuille de style d'une tuile-rangée au fil du
    survol : contour glissant du gris vers
    l'accent #3b9eff, fond de tuile distinct,
    enfants transparents.

    P18.6-bis série 6 (retour David, points 3a
    et 4) : mêmes canons que les GRANDES tuiles
    du hub (coins arrondis 12 px) ; les QFrame
    INTERNES (pages empilées une ligne / deux
    lignes) sont strictement TRANSPARENTS —
    sans cette règle, qdarktheme les repeint
    (#202124 en sombre) et masque le fond de
    la tuile, d'où la « légère différence de
    couleur sur les fonds » constatée.

    Le sélecteur racine est un sélecteur d'ID
    PUR (``#hub_tuile_reunion``) : la tuile du
    hub est un QWidget (les pages internes seules
    sont des QFrame) — l'ancien ``QFrame#…`` ne
    matchait JAMAIS la racine et le fond de la
    tuile ne s'affichait pas.
    """

    bord = melanger_couleurs(
        bord_base,
        BORD_BLEU_ACCENT,
        progression
    )

    return (
        f"#{nom_objet} {{"
        "border: 1px solid "
        + bord
        + ";"
        "border-radius: 12px;"
        "background-color: "
        + (
            melanger_couleurs(
                fond,
                fond_survol,
                progression
            )
        )
        + ";"
        "}"
        f"#{nom_objet} QWidget {{"
        "background-color: transparent;"
        "border: none;"
        "}}"
    )


class TuileReunion(QWidget):
    """
    Tuile-rangée d'une réunion du hub (spec 30f
    §26, compactée en P18.6-bis série 6 — retour
    David, point 3) : CLIQUABLE, sans bouton
    « Ouvrir », même langage graphique que les
    grandes tuiles (coins 12 px, contour visible,
    survol animé vers l'accent).

    Une ligne COMPACTE (~30 px — l'ancienne
    hauteur « mastoc » est divisée par deux) :
    marque carrée d'accent → titre → étude (ou
    mention « transcription en attente ») →
    stepper compact → coût à droite.

    Série 7 (retour David, point 3) : plus
    AUCUN lien « rattacher à une étude… » sur
    une réunion autonome — le rattachement se
    fait par le menu contextuel (clic droit) ;
    la rangée reste ainsi de hauteur IDENTIQUE
    d'une réunion à l'autre, les steppers sont
    alignés (point 4).

    Deux lignes en fenêtre étroite (titre + étude /
    stepper + coût), hauteur adaptative : la
    hauteur de la tuile suit la page EMPILÉE
    courante (le QStackedLayout réclame sinon la
    hauteur de la plus haute des deux pages).

    Le clic GAUCHE ouvre la réunion (le clic
    droit est traité par le menu contextuel du
    hub) ; le stepper n'est qu'un indicateur —
    jamais un lien vers chaque étape.
    """

    ouvrir_demandee = Signal(str)

    LARGEUR_UNE_LIGNE = 640
    MARGES = (12, 6, 12, 6)

    def __init__(
        self,
        chemin: str,
        titre: str,
        texte_etude,
        fabrique_stepper,
        cout: str,
        mention_non_transcrite: str = None,
        parent=None
    ):
        super().__init__(parent)

        self.chemin = chemin
        self.titre = titre

        self.setObjectName("hub_tuile_reunion")

        #
        # Contenu « une ligne » et contenu « deux
        # lignes », empilés : le resizeEvent bascule
        # selon la largeur, la hauteur suit le
        # contenu (adaptative).
        #
        racine = QVBoxLayout(self)
        racine.setContentsMargins(0, 0, 0, 0)
        racine.setSpacing(0)

        self.pile = QStackedLayout()
        racine.addLayout(self.pile)

        une_ligne = self._construire_une_ligne(
            texte_etude,
            fabrique_stepper,
            cout,
            mention_non_transcrite,
        )

        deux_lignes = self._construire_deux_lignes(
            texte_etude,
            fabrique_stepper,
            cout,
            mention_non_transcrite,
        )

        self.page_une_ligne = une_ligne
        self.page_deux_lignes = deux_lignes

        self.pile.addWidget(une_ligne)
        self.pile.addWidget(deux_lignes)

        self._appliquer_style(0.0)

        activer_survol_anime(
            self,
            self._appliquer_style
        )

        # Hauteur initiale alignée sur la page
        # courante (corrigée à chaque resize).
        self._basculer_selon_largeur(self.width())

    # ==================================================
    # Contenu.
    # ==================================================

    def _marque_accent(self) -> QLabel:
        """
        Marque carrée d'accent (#3b9eff) avec un
        léger halo de même teinte (§23).
        """

        marque = QLabel()
        marque.setFixedSize(10, 10)

        marque.setStyleSheet(
            "background-color: "
            + BORD_BLEU_ACCENT
            + ";"
            "border: 1px solid "
            "rgba(59,158,255,90);"
            "border-radius: 2px;"
        )

        return marque

    def _libelle_titre(self) -> QLabel:
        """
        Titre de la réunion, en gras.

        La graisse est posée par QFont (et non par
        la feuille de style) : un ``font-weight`` de
        feuille de style ne se reflète pas dans le
        sizeHint du label, qui réclamait alors une
        largeur erronée.
        """

        titre_label = QLabel(self.titre)

        police = QFont(self.font())
        police.setBold(True)
        titre_label.setFont(police)

        self.titre_label = titre_label

        return titre_label

    def _libelle_secondaire(
        self,
        texte_etude,
        mention_non_transcrite
    ):
        """
        Libellé secondaire INLINE (plus de colonne
        empilée — la rangée tient sur une ligne) :
        étude en couleur atténuée, ou mention
        « transcription en attente » pour une
        réunion non transcrite.

        Réunion autonome (série 7, retour David
        point 3) : AUCUN libellé — le
        rattachement se fait par le menu
        contextuel.
        """

        if mention_non_transcrite is not None:

            mention = QLabel(mention_non_transcrite)

            police = QFont(self.font())
            police.setPixelSize(11)
            police.setItalic(True)
            mention.setFont(police)

            mention.setStyleSheet(
                "color: #8a8b92;"
            )

            return mention

        if not texte_etude:
            return None

        etude_label = QLabel(texte_etude)

        police = QFont(self.font())
        police.setPixelSize(12)
        etude_label.setFont(police)

        etude_label.setStyleSheet(
            "color: #8a8b92;"
        )

        return etude_label

    def _zone_infos(
        self,
        fabrique_stepper,
        cout,
        aligne_droite: bool
    ):
        """
        Stepper compact + coût (alignés à droite).
        Chaque page empilée construit SON stepper
        (un même widget ne peut appartenir à deux
        layouts).
        """

        zone = QWidget()
        ligne = QHBoxLayout(zone)
        ligne.setContentsMargins(0, 0, 0, 0)
        ligne.setSpacing(12)

        if fabrique_stepper is not None:
            ligne.addWidget(fabrique_stepper())

        cout_label = QLabel(cout)

        police = QFont(self.font())
        police.setPixelSize(11)
        cout_label.setFont(police)

        cout_label.setStyleSheet(
            "color: #8a8b92;"
        )

        if aligne_droite:
            ligne.addStretch()

        ligne.addWidget(cout_label)

        self.cout_label = cout_label

        return zone

    def _construire_une_ligne(
        self,
        texte_etude,
        fabrique_stepper,
        cout,
        mention_non_transcrite
    ):
        """
        Disposition large : TOUT SUR UNE LIGNE —
        marque, titre, étude (ou mention),
        stepper, coût (retour David, point 3b :
        hauteur de rangée divisée par deux).
        """

        page = QFrame()
        page.setObjectName("hub_tuile_contenu")

        ligne = QHBoxLayout(page)
        ligne.setContentsMargins(*self.MARGES)
        ligne.setSpacing(10)

        ligne.addWidget(
            self._marque_accent()
        )

        ligne.addWidget(
            self._libelle_titre()
        )

        secondaire = self._libelle_secondaire(
            texte_etude,
            mention_non_transcrite
        )

        if secondaire is not None:
            ligne.addSpacing(4)
            ligne.addWidget(secondaire)

        ligne.addStretch()

        ligne.addWidget(
            self._zone_infos(fabrique_stepper, cout, False)
        )

        return page

    def _construire_deux_lignes(
        self,
        texte_etude,
        fabrique_stepper,
        cout,
        mention_non_transcrite
    ):
        """
        Disposition étroite : titre + étude, puis
        stepper + coût.
        """

        page = QFrame()
        page.setObjectName("hub_tuile_contenu")

        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(*self.MARGES)
        colonne.setSpacing(4)

        premiere = QHBoxLayout()
        premiere.setSpacing(10)

        premiere.addWidget(
            self._marque_accent()
        )

        premiere.addWidget(
            self._libelle_titre()
        )

        secondaire = self._libelle_secondaire(
            texte_etude,
            mention_non_transcrite
        )

        if secondaire is not None:
            premiere.addSpacing(4)
            premiere.addWidget(
                secondaire,
                stretch=1
            )
        else:
            premiere.addStretch()

        colonne.addLayout(premiere)

        deuxieme = QHBoxLayout()
        deuxieme.setSpacing(0)
        deuxieme.addStretch()
        deuxieme.addWidget(
            self._zone_infos(fabrique_stepper, cout, False)
        )

        colonne.addLayout(deuxieme)

        return page

    # ==================================================
    # Style (contour glissant au survol).
    # ==================================================

    def _appliquer_style(self, progression: float):

        couleurs = couleurs_tuiles(
            est_sombre(self)
        )

        self.setStyleSheet(
            style_rangee(
                self,
                "hub_tuile_reunion",
                couleurs["bord"],
                couleurs["fond"],
                couleurs["fond_survol"],
                progression,
            )
        )

    # ==================================================
    # Adaptation à la largeur (§26 : une ligne /
    # deux lignes en fenêtre étroite).
    # ==================================================

    def _basculer_selon_largeur(self, largeur: int):
        """
        Bascule entre la page « une ligne » (large)
        et la page « deux lignes » (fenêtre étroite)
        selon la largeur effective.

        La HAUTEUR de la tuile suit la page courante :
        le QStackedLayout réclame sinon la hauteur
        de la PLUS HAUTE des deux pages (l'ancien
        « mastoc » de 80 px, retour David point 3b).
        """

        cible = (
            self.page_deux_lignes
            if largeur < self.LARGEUR_UNE_LIGNE
            else self.page_une_ligne
        )

        if self.pile.currentWidget() is not cible:
            self.pile.setCurrentWidget(cible)

        self.setMaximumHeight(
            cible.sizeHint().height()
        )

    def resizeEvent(self, event):

        self._basculer_selon_largeur(self.width())

        super().resizeEvent(event)

    # ==================================================
    # Clic = ouverture (pas de bouton « Ouvrir »).
    # ==================================================

    def mousePressEvent(self, event):
        """
        Clic GAUCHE uniquement (retour David, point
        3c) : le clic droit relève du menu contextuel
        du hub. Le stepper n'est pas cliquable —
        c'est le clic sur la tuile qui ouvre la
        réunion à l'étape en cours.
        """

        if (
            event is None
            or event.button()
            == Qt.MouseButton.LeftButton
        ):
            self.ouvrir_demandee.emit(self.chemin)

        if event is not None:
            super().mousePressEvent(event)
