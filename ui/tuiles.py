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
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
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
OPACITE_OMBRE_SURVOL = 0.08


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
    ombre.setBlurRadius(24)
    ombre.setOffset(0, 8)
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
    """

    bord = melanger_couleurs(
        bord_base,
        BORD_BLEU_ACCENT,
        progression
    )

    return (
        f"QFrame#{nom_objet} {{"
        "border: 1px solid "
        + bord
        + ";"
        "border-radius: 8px;"
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
        f"QFrame#{nom_objet} QLabel {{"
        "background-color: transparent;"
        "border: none;"
        "}}"
        f"QFrame#{nom_objet} QPushButton {{"
        "background-color: transparent;"
        "border: none;"
        "}}"
    )


class TuileReunion(QWidget):
    """
    Tuile-rangée d'une réunion du hub (spec 30f
    §26) : CLIQUABLE, sans bouton « Ouvrir ».

    Une ligne : marque carrée d'accent (avec halo
    de même teinte) → titre → étude (couleur
    standard, ou lien « rattacher à une étude… »
    pour une réunion autonome) → stepper compact
    → infos (coût) à droite.

    Deux lignes en fenêtre étroite (titre + étude /
    stepper + infos), hauteur adaptative.
    """

    ouvrir_demandee = Signal(str)
    rattacher_demande = Signal(str)

    LARGEUR_UNE_LIGNE = 640

    def __init__(
        self,
        chemin: str,
        titre: str,
        texte_etude,
        lien_rattachement: bool,
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
            lien_rattachement,
            fabrique_stepper,
            cout,
            mention_non_transcrite,
        )

        deux_lignes = self._construire_deux_lignes(
            texte_etude,
            lien_rattachement,
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

    def _zone_etude(
        self,
        texte_etude,
        lien_rattachement,
        mention_non_transcrite
    ):
        """
        Zone titre + étude : le titre en gras,
        l'étude en couleur standard ; pour une
        réunion autonome, le lien « rattacher à
        une étude… » (cliquable).
        """

        zone = QWidget()
        colonne = QVBoxLayout(zone)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(1)

        titre_label = QLabel(self.titre)
        titre_label.setStyleSheet(
            "font-weight: 600;"
        )

        colonne.addWidget(titre_label)

        if mention_non_transcrite is not None:

            mention = QLabel(
                mention_non_transcrite
            )
            mention.setStyleSheet(
                "color: #8a8b92;"
                "font-style: italic;"
                "font-size: 11px;"
            )

            colonne.addWidget(mention)

        elif lien_rattachement:

            lien = QPushButton(
                "rattacher à une étude…"
            )
            lien.setFlat(True)
            lien.setCursor(
                Qt.CursorShape.PointingHandCursor
            )
            lien.setStyleSheet(
                "color: "
                + BORD_BLEU_ACCENT
                + ";"
                "text-decoration: underline;"
                "border: none;"
                "padding: 0;"
                "font-size: 12px;"
                "text-align: left;"
            )
            lien.clicked.connect(
                lambda checked=False: (
                    self.rattacher_demande.emit(
                        self.chemin
                    )
                )
            )

            colonne.addWidget(lien)

        else:

            etude_label = QLabel(texte_etude)
            etude_label.setStyleSheet(
                "font-size: 12px;"
            )

            colonne.addWidget(etude_label)

        self.titre_label = titre_label

        return zone

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
        cout_label.setStyleSheet(
            "color: #8a8b92; font-size: 11px;"
        )

        if aligne_droite:
            ligne.addStretch()

        ligne.addWidget(cout_label)

        self.cout_label = cout_label

        return zone

    def _construire_une_ligne(
        self,
        texte_etude,
        lien_rattachement,
        fabrique_stepper,
        cout,
        mention_non_transcrite
    ):
        """
        Disposition large : tout sur UNE ligne.
        """

        page = QFrame()
        page.setObjectName("hub_tuile_contenu")

        ligne = QHBoxLayout(page)
        ligne.setContentsMargins(10, 8, 10, 8)
        ligne.setSpacing(10)

        ligne.addWidget(
            self._marque_accent()
        )

        ligne.addWidget(
            self._zone_etude(
                texte_etude,
                lien_rattachement,
                mention_non_transcrite
            ),
            stretch=1
        )

        ligne.addWidget(
            self._zone_infos(fabrique_stepper, cout, True)
        )

        return page

    def _construire_deux_lignes(
        self,
        texte_etude,
        lien_rattachement,
        fabrique_stepper,
        cout,
        mention_non_transcrite
    ):
        """
        Disposition étroite : titre + étude, puis
        stepper + infos.
        """

        page = QFrame()
        page.setObjectName("hub_tuile_contenu")

        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(10, 8, 10, 8)
        colonne.setSpacing(4)

        premiere = QHBoxLayout()
        premiere.setSpacing(10)

        premiere.addWidget(
            self._marque_accent()
        )

        premiere.addWidget(
            self._zone_etude(
                texte_etude,
                lien_rattachement,
                mention_non_transcrite
            ),
            stretch=1
        )

        colonne.addLayout(premiere)

        colonne.addWidget(
            self._zone_infos(fabrique_stepper, cout, True)
        )

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
        """

        cible = (
            self.page_deux_lignes
            if largeur < self.LARGEUR_UNE_LIGNE
            else self.page_une_ligne
        )

        if self.pile.currentWidget() is not cible:
            self.pile.setCurrentWidget(cible)

    def resizeEvent(self, event):

        self._basculer_selon_largeur(self.width())

        super().resizeEvent(event)

    # ==================================================
    # Clic = ouverture (pas de bouton « Ouvrir »).
    # ==================================================

    def mousePressEvent(self, event):

        self.ouvrir_demandee.emit(self.chemin)

        if event is not None:
            super().mousePressEvent(event)
