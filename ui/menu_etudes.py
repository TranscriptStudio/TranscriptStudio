# ui/menu_etudes.py
"""
Menu déroulant « Études » du hub (P18.6-bis,
série 4 — maquette validée) : panneau ancré à la
tuile, et non une liste de menu brute.

Structure de la maquette :

- en-tête « VOS ÉTUDES » (majuscules, espacé) ;
- une LIGNE par étude : pastille de couleur, nom,
  « [thème] · modifiée le [date] », badge
  « N réunions » ;
- séparateur ;
- actions « ＋ Nouvelle étude… » et
  « Ouvrir depuis un dossier… » ;
- sans étude : « Aucune étude pour le moment »
  suivi des deux actions.

Échap ou clic extérieur referment le menu
(Qt.Popup + touche Échap). Choisir une étude
ouvre directement la page Étude.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from services.settings import SettingsManager
from services.theme_manager import (
    BORD_BLEU_ACCENT,
    couleurs_menu_etudes,
    est_sombre,
)

LARGEUR_MENU = 320

#
# Pastille de couleur par étude (maquette : bleu
# d'accent pour l'une, orange pour l'autre) — la
# teinte est stable pour une même étude
# (déterminée par son dossier, aucune donnée
# n'est stockée).
#
PALETTE_PASTILLES = (
    "#3b9eff",
    "#b57a4a",
    "#5aa06e",
    "#8d6fb5",
    "#b55a6e",
)

MOIS_COURTS = (
    "janv.", "févr.", "mars", "avr.",
    "mai", "juin", "juil.", "août",
    "sept.", "oct.", "nov.", "déc.",
)


def couleur_pastille(dossier) -> str:
    """
    Couleur de la pastille d'une étude, stable
    pour un même dossier.
    """

    total = sum(
        ord(c) for c in str(dossier)
    )

    return PALETTE_PASTILLES[
        total % len(PALETTE_PASTILLES)
    ]


def formater_date_modification(horodatage: str) -> str:
    """
    « modifiée le 27 oct. 2026 » à partir d'un
    horodatage ISO ``AAAA-MM-JJ…`` (champ
    ``modification`` d'etude.json). Chaîne vide si
    illisible.
    """

    if not horodatage or len(horodatage) < 10:
        return ""

    try:

        annee = int(horodatage[0:4])
        mois = int(horodatage[5:7])
        jour = int(horodatage[8:10])

    except ValueError:
        return ""

    if not 1 <= mois <= 12:
        return ""

    return (
        f"modifiée le {jour} "
        f"{MOIS_COURTS[mois - 1]} {annee}"
    )


def libelle_theme(theme: str) -> str:
    """
    « Livre biblique » / « Thème libre » (ou le
    thème libre saisi tel quel).
    """

    return {
        "livre": "Livre biblique",
        "libre": "Thème libre",
    }.get(theme, theme or "")


class LigneEtude(QWidget):
    """
    Une ligne d'étude du menu : pastille, nom,
    thème · date de modification, badge
    « N réunions ». Clic = choix de l'étude.
    """

    cliquee = Signal(str)

    def __init__(self, dossier, parent=None):

        super().__init__(parent)

        self.dossier = str(dossier)

        self.setObjectName("menu_etudes_item")

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        # Sous-classe de QWidget : sans cet
        # attribut, le survol :hover (fond de
        # ligne) ne se rend jamais.
        self.setAttribute(
            Qt.WidgetAttribute
            .WA_StyledBackground,
            True
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        pastille = QLabel()
        pastille.setFixedSize(10, 10)
        pastille.setStyleSheet(
            "border-radius: 3px;"
            "background-color: "
            + couleur_pastille(dossier)
            + ";"
        )

        layout.addWidget(pastille)

        textes = QVBoxLayout()
        textes.setContentsMargins(0, 0, 0, 0)
        textes.setSpacing(1)

        nom = QLabel(parent=None)
        self.nom_label = nom
        textes.addWidget(nom)

        detail = QLabel()
        self.detail_label = detail
        textes.addWidget(detail)

        layout.addLayout(textes, stretch=1)

        badge = QLabel()
        self.badge_label = badge
        layout.addWidget(badge)

    def definir_contenu(
        self,
        titre: str,
        detail: str,
        nb_reunions: int
    ):
        """
        Remplit la ligne (séparé du constructeur
        pour les tests).
        """

        pluriel = "s" if nb_reunions > 1 else ""

        self.nom_label.setText(titre)
        self.detail_label.setText(detail)
        self.badge_label.setText(
            f"{nb_reunions} réunion{pluriel}"
        )

    def mousePressEvent(self, event):

        self.cliquee.emit(self.dossier)

        super().mousePressEvent(event)


class LigneAction(QWidget):
    """
    Une ligne d'action du menu (« ＋ Nouvelle
    étude… », « Ouvrir depuis un dossier… »).
    """

    cliquee = Signal()

    SYMBOLE_NOUVELLE = "＋"

    def __init__(
        self,
        libelle: str,
        symbole: str = None,
        icone: str = None,
        parent=None
    ):

        super().__init__(parent)

        self.setObjectName("menu_etudes_item")

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setAttribute(
            Qt.WidgetAttribute
            .WA_StyledBackground,
            True
        )

        self.libelle = libelle

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        if icone is not None:

            icone_label = QLabel()
            pixmap = QPixmap(icone)
            icone_label.setPixmap(
                pixmap.scaled(
                    14,
                    14,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

            layout.addWidget(icone_label)

        else:

            symbole_label = QLabel(symbole or "")
            symbole_label.setStyleSheet(
                "font-size: 14px;"
                "border: none;"
            )

            layout.addWidget(symbole_label)

        nom = QLabel(libelle)
        self.nom_label = nom

        layout.addWidget(nom, stretch=1)

    def mousePressEvent(self, event):

        self.cliquee.emit()

        super().mousePressEvent(event)


class MenuEtudes(QWidget):
    """
    Panneau déroulant des études, ancré sous la
    tuile « Études » du hub (maquette P18.6-bis
    série 4) — 320 px de large, coins arrondis,
    ombre portée, en-tête, lignes d'études,
    séparateur, actions.

    Signaux :
    - ``etude_choisie(chemin_dossier)`` : ouvrir
      directement la page Étude ;
    - ``nouvelle_etude()`` ;
    - ``ouvrir_dossier()``.
    """

    etude_choisie = Signal(str)
    nouvelle_etude = Signal()
    ouvrir_dossier = Signal()

    TEXTE_ENTETE = "Vos études"
    TEXTE_VIDE = "Aucune étude présente."

    def __init__(
        self,
        settings: SettingsManager,
        parent=None
    ):
        super().__init__(
            parent,
            Qt.WindowType.Popup
            | Qt.FramelessWindowHint
        )

        self.settings = settings

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        self.setFixedWidth(LARGEUR_MENU)

        self.lignes = []

        self._construire()

    # ==================================================
    # Construction.
    # ==================================================

    def _couleurs(self) -> dict:

        return couleurs_menu_etudes(
            est_sombre(self)
        )

    def _construire(self):

        couleurs = self._couleurs()

        self.conteneur = QFrame()
        self.conteneur.setObjectName(
            "menu_etudes_conteneur"
        )

        self.conteneur.setStyleSheet(
            "QFrame#menu_etudes_conteneur {"
            "background-color: "
            + couleurs["fond"]
            + ";"
            "border: 1px solid "
            + couleurs["bord"]
            + ";"
            "border-radius: 12px;"
            "}"
            "QWidget#menu_etudes_item {"
            "background: transparent;"
            "border: none;"
            "}"
            "QWidget#menu_etudes_item:hover {"
            "background-color: "
            + couleurs["survol_item"]
            + ";"
            "}"
            "QLabel {"
            "border: none;"
            "background: transparent;"
            "}"
            "QWidget#menu_etudes_item QLabel {"
            "border: none;"
            "background-color: transparent;"
            "}"
        )

        #
        # Ombre portée de la maquette.
        #
        ombre = QGraphicsDropShadowEffect(self)
        ombre.setBlurRadius(26)
        ombre.setOffset(0, 10)
        ombre.setColor(
            Qt.GlobalColor.black
        )

        self.conteneur.setGraphicsEffect(ombre)

        racine = QVBoxLayout(self)
        racine.setContentsMargins(0, 0, 0, 0)
        racine.addWidget(self.conteneur)

        layout = QVBoxLayout(self.conteneur)
        layout.setContentsMargins(0, 0, 0, 6)
        layout.setSpacing(0)

        #
        # En-tête « VOS ÉTUDES » (majuscules,
        # espacées — QFont::setLetterSpacing).
        #
        entete = QLabel(self.TEXTE_ENTETE)
        entete.setObjectName("menu_etudes_entete")

        police = QFont()
        police.setPointSizeF(8.5)
        police.setLetterSpacing(
            QFont.SpacingType.AbsoluteSpacing,
            0.8
        )

        entete.setFont(police)
        entete.setStyleSheet(
            "color: " + couleurs["entete"] + ";"
            "text-transform: uppercase;"
            "padding: 10px 14px 6px 14px;"
        )

        layout.addWidget(entete)

        #
        # Lignes des études (ou l'indication
        # d'absence).
        #
        from services.rattachement import (
            lire_etude_legere,
            reunions_des_etudes,
        )

        etudes = (
            self.settings.cleanup_recent_etudes()
        )

        if not etudes:

            vide = QLabel(self.TEXTE_VIDE)
            vide.setStyleSheet(
                "color: " + couleurs["detail"] + ";"
                "font-size: 12px;"
                "padding: 10px 14px;"
            )

            layout.addWidget(vide)

        else:

            for dossier in etudes:

                ligne = LigneEtude(dossier)
                ligne.cliquee.connect(
                    self._choisir_etude
                )

                infos = lire_etude_legere(dossier)

                titre = (
                    (infos or {}).get("titre")
                    or Path(dossier).name
                )

                theme = libelle_theme(
                    (infos or {}).get("theme", "")
                )

                modification = formater_date_modification(
                    (infos or {}).get(
                        "modification", ""
                    )
                )

                detail = " · ".join(
                    partie
                    for partie in (
                        theme,
                        modification,
                    )
                    if partie
                )

                ligne.definir_contenu(
                    titre,
                    detail,
                    len(
                        reunions_des_etudes(
                            dossier
                        )
                    )
                )

                self._styliser_ligne(ligne)

                layout.addWidget(ligne)

                self.lignes.append(ligne)

        self._ajouter_separateur(layout)

        #
        # Actions : « ＋ Nouvelle étude… » et
        # « Ouvrir depuis un dossier… ».
        #
        from services.resources import (
            resource_path,
        )

        action_nouvelle = LigneAction(
            "Nouvelle étude",
            symbole=LigneAction.SYMBOLE_NOUVELLE
        )

        action_nouvelle.cliquee.connect(
            self._demander_nouvelle
        )

        self._styliser_ligne(action_nouvelle)

        layout.addWidget(action_nouvelle)

        action_ouvrir = LigneAction(
            "Ouvrir depuis un dossier…",
            icone=str(
                resource_path(
                    "icons/tuile-reprendre.svg"
                )
            )
        )

        action_ouvrir.cliquee.connect(
            self._demander_ouvrir
        )

        self._styliser_ligne(action_ouvrir)

        layout.addWidget(action_ouvrir)

        self.action_nouvelle = action_nouvelle
        self.action_ouvrir = action_ouvrir

    def _styliser_ligne(self, ligne: QWidget):
        """
        Typographie des lignes (nom, détail, badge)
        — séparée de la construction pour les tests.
        """

        couleurs = self._couleurs()

        if hasattr(ligne, "detail_label"):

            ligne.nom_label.setStyleSheet(
                "font-size: 13px;"
                "font-weight: 600;"
            )

            ligne.detail_label.setStyleSheet(
                "font-size: 11px;"
                "color: "
                + couleurs["detail"]
                + ";"
            )

            ligne.badge_label.setStyleSheet(
                "font-size: 10.5px;"
                "color: "
                + couleurs["badge_texte"]
                + ";"
                "background-color: "
                + couleurs["badge_fond"]
                + ";"
                "border: 1px solid "
                + couleurs["badge_bord"]
                + ";"
                "border-radius: 12px;"
                "padding: 2px 8px;"
            )

        else:

            ligne.nom_label.setStyleSheet(
                "font-size: 13px;"
                "font-weight: 500;"
                "color: #c2d0e2;"
            )

    def _ajouter_separateur(self, layout):

        couleurs = self._couleurs()

        separateur = QFrame()
        separateur.setFixedHeight(1)
        separateur.setStyleSheet(
            "background-color: "
            + couleurs["separateur"]
            + ";"
            "border: none;"
            "margin: 6px 0;"
        )

        layout.addWidget(separateur)

    # ==================================================
    # Actions du menu.
    # ==================================================

    def _choisir_etude(self, dossier: str):

        self.close()

        self.etude_choisie.emit(dossier)

    def _demander_nouvelle(self):

        self.close()

        self.nouvelle_etude.emit()

    def _demander_ouvrir(self):

        self.close()

        self.ouvrir_dossier.emit()

    # ==================================================
    # Ouverture / fermeture.
    # ==================================================

    def ouvrir_sous(self, tuile: QWidget):
        """
        Ancle le panneau SOUS la tuile (gauche
        alignée, 8 px d'écart — maquette), le
        montre et prend le focus (Échap referme).
        """

        from PySide6.QtCore import QPoint

        point = tuile.mapToGlobal(
            QPoint(0, tuile.height() + 8)
        )

        self.move(point)
        self.show()
        self.setFocus()

    def keyPressEvent(self, event):
        """
        Échap referme le menu.
        """

        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return

        super().keyPressEvent(event)
