# ui/stepper.py
"""
Barre d'étapes du stepper de réunion (P18.6,
spec navigation §3.2) : ① Prétraitement ·
② Transcription · ③ Correction · ④ Reformulation ·
⑤ Résumé · ⑥ Export.

Couleurs : gris (à faire) / bleu (en cours) /
vert (terminé). P18.6-bis (spec correctifs §18) :
PLUS AUCUN contour pointillé — aucune différence
visuelle entre étapes obligatoires et
optionnelles ; l'optionnalité ne se lit que dans
le bouton « Étape suivante : … (optionnelle) »
et l'info-bulle au survol.

Réutilisé par :
- la page Réunion (stepper fixe, cliquable) ;
- la page Étude (avancement ①→⑤ sans ⑥,
  invariant §9.4) ;
- les mini-tuiles du hub et de la page Étude.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from services.avancement import (
    A_FAIRE,
    EN_COURS,
    ETAPES_OPTIONNELLES,
    ETAPES_REUNION,
    LIBELLES_ETAPES,
    TERMINE,
)

STYLES_ETATS = {
    A_FAIRE: (
        "border: 1px solid #9E9E9E;"
        "color: #8A8A8A;"
        "background: transparent;"
    ),
    EN_COURS: (
        "border: 1px solid #2196F3;"
        "color: #1565C0;"
        "background: rgba(33, 150, 243, 0.08);"
    ),
    TERMINE: (
        "border: 1px solid #4CAF50;"
        "color: #2E7D32;"
        "background: rgba(76, 175, 80, 0.08);"
    ),
}


class StepperBar(QWidget):
    """
    Stepper horizontal : une pastille par étape,
    couleur selon l'état, contour pointillé pour
    les étapes optionnelles.

    ``etape_cliquee`` est émis avec la clé de
    l'étape (navigation directe de la page
    Réunion ; le hub ignore le signal).
    """

    etape_cliquee = Signal(str)

    def __init__(
        self,
        etapes=ETAPES_REUNION,
        optionnelles=ETAPES_OPTIONNELLES,
        cliquable=True,
        compact=False,
        parent=None
    ):
        super().__init__(parent)

        self.etapes = tuple(etapes)
        self.optionnelles = tuple(optionnelles)
        self._compact = compact

        self.setObjectName("stepper_reunion")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.boutons = {}

        for etape in self.etapes:

            bouton = QPushButton(
                LIBELLES_ETAPES[etape]
            )

            if etape in self.optionnelles:
                bouton.setToolTip(
                    "Étape optionnelle"
                )

            bouton.setFlat(True)
            bouton.setCursor(self.cursor())

            bouton.setStyleSheet(
                self._style(etape, A_FAIRE)
            )

            if compact:
                bouton.setToolTip(
                    LIBELLES_ETAPES[etape]
                )

            if cliquable:

                bouton.clicked.connect(
                    lambda checked=False,
                    cle=etape: (
                        self.etape_cliquee.emit(
                            cle
                        )
                    )
                )

            else:
                bouton.setDisabled(True)

            layout.addWidget(bouton)

            self.boutons[etape] = bouton

        layout.addStretch()

    def _style(
        self,
        etape: str,
        etat: str
    ) -> str:
        """
        Feuille de style d'une pastille : couleur
        d'état. Toutes les pastilles ont le même
        contour (spec correctifs §18).
        """

        style = STYLES_ETATS.get(
            etat,
            STYLES_ETATS[A_FAIRE]
        )

        return (
            style
            + "border-radius: 10px;"
            "padding: 1px 8px;"
            "font-size: "
            + ("10px" if self.isCompact else "12px")
            + ";"
        )

    def definir_etats(self, etats: dict):
        """
        Met à jour la couleur de chaque pastille
        (états du service d'avancement ; une étape
        absente repasse à faire).
        """

        for etape, bouton in (
            self.boutons.items()
        ):

            etat = etats.get(etape, A_FAIRE)

            bouton.setStyleSheet(
                self._style(etape, etat)
            )

    @property
    def isCompact(self) -> bool:
        return getattr(self, "_compact", False)
