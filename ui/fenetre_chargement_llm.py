# ui/fenetre_chargement_llm.py
"""
Fenêtre de chargement affichée pendant TOUTE
interrogation du LLM de l'app (règle David,
2026-11-07) :

- barre de progression DÉTERMINÉE quand c'est
  possible (ex. passe de reformulation :
  « Bloc k/N », segments du résumé :
  « Segment k/N », avec estimation du temps
  restant à titre indicatif) ;
- sinon barre INDÉTERMINÉE (un seul appel :
  relance d'un bloc, relance ciblée, synthèse,
  fusion assistée) ;
- le TEMPS ÉCOULÉ est TOUJOURS affiché
  (m:ss, h:mm:ss au-delà d'une heure) ;
- bouton « Annuler » branché sur l'objet
  d'annulation de l'opération.

La fenêtre est NON MODALE (show) : la page
reste visible et réactive derrière.
"""

import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)


def formater_duree(secondes) -> str:
    """
    m:ss, ou h:mm:ss au-delà d'une heure.
    """

    secondes = max(0, int(secondes))

    heures = secondes // 3600
    minutes = (secondes % 3600) // 60
    s = secondes % 60

    if heures:
        return f"{heures}:{minutes:02d}:{s:02d}"

    return f"{minutes}:{s:02d}"


def formater_restant(secondes) -> str:
    """
    Estimation indicative : « ~45 s » ou
    « ~2 min ».
    """

    secondes = max(0, int(secondes))

    if secondes < 90:
        return f"~{secondes} s"

    return f"~{round(secondes / 60)} min"


class FenetreChargementLLM(QDialog):
    """
    Fenêtre de chargement d'une interrogation
    LLM : titre + étape courante, barre
    (déterminée si total connu), temps écoulé,
    estimation du restant, Annuler.
    """

    def __init__(
        self,
        titre: str,
        parent=None,
        annulation=None,
        message: str = "Appel LLM en cours…",
        unite: str = "Bloc"
    ):
        super().__init__(parent)

        self.setWindowTitle(titre)
        self.setModal(False)

        self.annulation = annulation
        self.unite = unite

        self._depart = time.monotonic()
        self._total = 0
        self._traites = 0
        self._fermee = False
        self._message = message

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        self.etape_label = QLabel(message)
        self.etape_label.setWordWrap(True)

        layout.addWidget(self.etape_label)

        self.barre = QProgressBar()
        self.barre.setTextVisible(False)
        self.barre.setFixedHeight(8)
        self.barre.setRange(0, 0)

        layout.addWidget(self.barre)

        self.temps_label = QLabel(
            "Temps écoulé : 0:00"
        )
        layout.addWidget(self.temps_label)

        self.restant_label = QLabel("")
        self.restant_label.setStyleSheet(
            "color: #8a8b92; font-size: 11px;"
        )
        layout.addWidget(self.restant_label)

        boutons = QHBoxLayout()
        boutons.addStretch(1)

        self.annuler_button = QPushButton("Annuler")

        if annulation is None:
            self.annuler_button.setVisible(False)
        else:
            self.annuler_button.clicked.connect(
                self.annuler
            )

        boutons.addWidget(self.annuler_button)

        layout.addLayout(boutons)

        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.maj_temps)
        self.timer.start()

        self.maj_temps()

    #
    # Progression.
    #

    def set_total(self, total: int, base: int = 0):
        """
        Barre DÉTERMINÉE : total connu (base =
        unités déjà faites avant ce lancement,
        ex. reprise après annulation).
        """

        self._total = max(0, int(total))
        self._traites = max(0, int(base))

        if self._total:
            self.barre.setRange(0, self._total)
            self.barre.setValue(self._traites)

        self._maj_etiquette()
        self.maj_temps()

    def definir_progression(
        self,
        traites: int,
        total: int = None
    ):
        """
        Avancer : k unités traitées sur total.
        """

        if total is not None:
            self._total = max(0, int(total))

        self._traites = max(0, int(traites))

        if self._total:
            self.barre.setRange(0, self._total)
            self.barre.setValue(self._traites)
        else:
            self.barre.setRange(0, 0)

        self._maj_etiquette()
        self.maj_temps()

    def set_indeterminee(self):
        """
        Barre INDÉTERMINÉE (un seul appel LLM).
        """

        self._total = 0
        self._traites = 0
        self.barre.setRange(0, 0)

        self.etape_label.setText(self._message)

        self.maj_temps()

    def _maj_etiquette(self):

        if self._total:
            self.etape_label.setText(
                f"{self.unite} {self._traites}"
                f"/{self._total} — en cours…"
            )

    #
    # Temps.
    #

    def maj_temps(self):

        ecoule = time.monotonic() - self._depart

        self.temps_label.setText(
            "Temps écoulé : "
            + formater_duree(ecoule)
        )

        if (
            self._total
            and self._traites > 0
            and self._traites < self._total
        ):
            restant = (
                ecoule
                * (self._total - self._traites)
                / self._traites
            )

            self.restant_label.setText(
                "Reste "
                + formater_restant(restant)
                + " (indicatif)"
            )

        else:
            self.restant_label.setText("")

    #
    # Annulation et fermeture.
    #

    def annuler(self):

        if self.annulation is not None:
            self.annulation.demandee = True

        self.annuler_button.setEnabled(False)

    def fermer(self):

        if self._fermee:
            return

        self._fermee = True

        self.timer.stop()

        self.close()
