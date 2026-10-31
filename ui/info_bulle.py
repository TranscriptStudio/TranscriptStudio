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

P20-bis (retour David 31/10, points 5-6) :
- la police et le fond sont recalculés à
  CHAQUE affichage (un changement de thème à
  chaud ne laisse plus l'info-bulle aux
  couleurs du thème précédent) ;
- la taille de police est EXPLICITE dans la
  feuille de style — la pastille parente
  portait « font-size: 20px » qui déteignait
  sur l'info-bulle enfant.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

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
        self._texte = ""

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
        # Police de l'app : celle du widget survolé
        # AVANT toute feuille de style (la pastille
        # grossit sa police par stylesheet —
        # l'info-bulle ne doit pas en hériter),
        # taille réduite d'un cran.
        #
        police = parent_widget.font()
        police.setPointSize(
            max(9, police.pointSize() - 1)
        )

        self.setFont(police)

        self._taille_police = (
            police.pointSize()
        )

    def definir_texte(self, texte: str):
        """
        Mémorise le texte (brut, retours à la ligne
        conservés) et l'applique au thème COURANT.
        """

        self._texte = texte

        self._appliquer()

    def _appliquer(self):
        """
        Restyle au thème APPLIQUÉ — appelé à chaque
        définition ET à chaque affichage : l'info-
        bulle suit les changements de thème à chaud.
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

        lignes = self._texte.split("\n")

        corps = "<br>".join(
            ligne.replace("<", "&lt;")
            for ligne in lignes
        )

        self.setText(
            f"<div style='color:{texte_couleur};'>"
            f"{corps}</div>"
        )

        self.setStyleSheet(
            "QLabel {"
            f"background-color: {fond};"
            f"color: {texte_couleur};"
            f"border: 1px solid {bord};"
            "border-radius: 6px;"
            f"font-size: {self._taille_police}pt;"
            "}"
        )

        self.adjustSize()

        if self.width() > self.LARGEUR_MAX:
            self.setFixedWidth(self.LARGEUR_MAX)
            self.adjustSize()

    def montrer(self):
        """
        Affiche l'info-bulle AU-DESSUS du widget
        survolé (ou en dessous si la place manque),
        dans le thème courant.
        """

        self._appliquer()

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
