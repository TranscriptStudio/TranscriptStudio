# ui/stepper.py
"""
Barre d'étapes du stepper de réunion (P18.6,
spec navigation §3.2) : ① Prétraitement ·
② Transcription · ③ Correction · ④ Reformulation ·
⑤ Résumé · ⑥ Export.

Couleurs affirmées (P18.6-bis série 5, spec 30f
§24, maquette hub v4) : à faire = gris discret ;
en cours = pastille pleine bleue à texte blanc,
lueur discrète ; fait = émeraude sur fond
translucide. P18.6-bis (§18) : PLUS AUCUN contour
pointillé — aucune différence
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

#
# Série 5 (spec 30f §24, maquette hub v4) :
# couleurs affirmées, identiques dans les deux
# thèmes — en cours = pastille PLEINE bleue à
# texte blanc avec lueur discrète ; fait =
# émeraude sur fond translucide ; à faire =
# gris discret.
#
from services.theme_manager import (
    COULEURS_STEPPER as _COULEURS_STEPPER,
)

STYLES_ETATS = {
    A_FAIRE: (
        "border: 1px solid "
        + _COULEURS_STEPPER["a_faire_fond"]
        + ";"
        "color: "
        + _COULEURS_STEPPER["a_faire_texte"]
        + ";"
        "background-color: "
        + _COULEURS_STEPPER["a_faire_fond"]
        + ";"
    ),
    EN_COURS: (
        "border: 1px solid "
        + _COULEURS_STEPPER["en_cours_lueur"]
        + ";"
        "color: "
        + _COULEURS_STEPPER["en_cours_texte"]
        + ";"
        "background-color: "
        + _COULEURS_STEPPER["en_cours_fond"]
        + ";"
    ),
    TERMINE: (
        "border: 1px solid "
        + _COULEURS_STEPPER["fait_contour"]
        + ";"
        "color: "
        + _COULEURS_STEPPER["fait_texte"]
        + ";"
        "background-color: "
        + _COULEURS_STEPPER["fait_fond"]
        + ";"
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
