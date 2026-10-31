"""
P20 (retour David 31/10, UI reformulation point 9)
: info-bulle au thème de l'APPLICATION.

L'info-bulle native de Qt (QToolTip) suit le
thème de l'OS, pas celui de l'app : en thème
clair elle restait noire, avec la police
système — et sans retour à la ligne.

InfoBulle : petit QLabel contextuel stylé dans
le thème APPLIQUÉ (fond, texte, bord), police
de l'app, texte MULTI-LIGNE (retour à la ligne
automatique sur une largeur maximale).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from services.icons import text_color_effectif
from services.theme_manager import est_sombre


class InfoBulle(QLabel):
    """
    Info-bulle contextuelle : montrer() au survol,
    cacher() à la sortie. Le texte peut être du
    HTML multi-ligne (largeur plafonnée).
    """

    LARGEUR_MAX = 260

    def __init__(self, parent_widget):

        super().__init__(parent_widget)

        self._parent = parent_widget

        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
        )

        self.setTextFormat(
            Qt.TextFormat.RichText
        )

        self.setWordWrap(True)

        self.setContentsMargins(8, 6, 8, 6)

        #
        # Police de l'app : celle du widget survolé,
        # taille réduite d'un cran.
        #
        police = parent_widget.font()
        police.setPointSize(
            max(9, police.pointSize() - 1)
        )

        self.setFont(police)

        self.definir_texte("")

    def definir_texte(self, texte: str):
        """
        Texte brut (retours à la ligne conservés) —
        restylé au thème courant à CHAQUE définition
        (l'info-bulle suit le thème appliqué, y
        compris après un changement à chaud).
        """

        sombre = est_sombre(self._parent)

        fond = "#26272d" if sombre else "#ffffff"
        texte_couleur = (
            "#d7d8dc" if sombre else "#404248"
        )
        bord = (
            "rgba(255,255,255,28)"
            if sombre
            else "#c4c7cf"
        )

        lignes = texte.split("\n")

        corps = "<br>".join(
            ligne.replace("<", "&lt;")
            for ligne in lignes
        )

        self.setText(
            f"<div style='color:{texte_couleur};'>"
            f"{corps}</div>"
        )

        self.setStyleSheet(
            f"QLabel {{"
            f"background-color: {fond};"
            f"color: {texte_couleur};"
            f"border: 1px solid {bord};"
            f"border-radius: 6px;"
            f"}}"
        )

        self.adjustSize()

        if self.width() > self.LARGEUR_MAX:
            self.setFixedWidth(self.LARGEUR_MAX)
            self.adjustSize()

    def montrer(self):
        """
        Affiche l'info-bulle AU-DESSUS du widget
        survolé (ou en dessous si la place manque).
        """

        zone = self._parent.rect()

        coin = self._parent.mapToGlobal(
            zone.topLeft()
        )

        x = coin.x()

        #
        # Centrée sur le widget, jamais hors écran
        # à gauche.
        #
        x += max(
            0,
            (zone.width() - self.width()) // 2
        )

        y = coin.y() - self.height() - 8

        ecran = self.screen()

        if ecran is not None:
            if y < ecran.availableGeometry().top():
                y = (
                    coin.y()
                    + zone.height()
                    + 8
                )

        self.move(x, y)

        self.show()

    def cacher(self):

        self.hide()
