# ui/log_window.py
"""
Page Log des opérations (P15.4 / P16, spec UI §8).

Lecture seule : texte déroulant, aucune édition ;
copie possible (« Copier tout » et copie de la
sélection) ; contenu du fichier log de l'étude
courante, rafraîchi à l'ouverture.
"""

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from services.traitements.journal import JournalEtude


class LogWindow(QDialog):
    """
    Affichage en lecture seule du log des
    opérations de l'étude.
    """

    def __init__(
        self,
        journal: JournalEtude,
        parent=None
    ):
        super().__init__(parent)

        self.journal = journal

        self.setWindowTitle(
            "📋 Log des opérations"
        )

        self.resize(820, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        entete = QLabel(
            "Journal de toutes les opérations de "
            "l'étude (lecture seule) : passes, "
            "reformulations, éditions, validations, "
            "fusions, erreurs, annulations."
        )
        entete.setWordWrap(True)
        layout.addWidget(entete)

        self.zone_texte = QPlainTextEdit()
        self.zone_texte.setReadOnly(True)
        self.zone_texte.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        police = self.zone_texte.font()
        police.setFamily("Consolas")
        self.zone_texte.setFont(police)

        layout.addWidget(self.zone_texte, stretch=1)

        boutons = QHBoxLayout()
        boutons.addStretch()

        self.copier_selection_button = QPushButton(
            "Copier la sélection"
        )
        self.copier_selection_button.clicked.connect(
            self.copier_selection
        )

        self.copier_tout_button = QPushButton(
            "Copier tout"
        )
        self.copier_tout_button.clicked.connect(
            self.copier_tout
        )

        self.fermer_button = QPushButton("Fermer")
        self.fermer_button.clicked.connect(self.accept)

        boutons.addWidget(self.copier_selection_button)
        boutons.addWidget(self.copier_tout_button)
        boutons.addWidget(self.fermer_button)

        layout.addLayout(boutons)

        self.rafraichir()

    def rafraichir(self):
        """
        Contenu du fichier log de l'étude, relu à
        l'ouverture de la page.
        """

        self.journal.charger()

        lignes = []

        for entree in self.journal.dernieres():

            parties = [
                str(entree.get("horodatage", "")),
                entree.get("type", ""),
            ]

            fid = entree.get("fid")

            if fid is not None:
                parties.append(f"FID {fid}")

            reunion = entree.get("reunion")

            if reunion:
                parties.append(reunion)

            modele = entree.get("modele")

            if modele:
                parties.append(modele)

            version = entree.get("version")

            if version is not None:
                parties.append(f"v{version}")

            ligne = " · ".join(parties)

            resultat = entree.get("resultat")

            if resultat:
                ligne += f" — {resultat}"

            message = entree.get("message")

            if message:
                ligne += f" : {message}"

            stats = entree.get("stats")

            if stats:

                ligne += (
                    f" [{stats.get('duree_ms', 0)}ms · "
                    f"{stats.get('tokens_in', 0)}→"
                    f"{stats.get('tokens_out', 0)} tokens · "
                    f"{stats.get('cout_estime', 0.0):.4f} €]"
                )

            extras = ""

            for cle in (
                "statut",
                "nb_blocs",
                "blocs_traites",
                "cible",
                "cout_total",
                "type_version",
                "source",
            ):

                if cle in entree:
                    extras += f" {cle}={entree[cle]}"

            if extras:
                ligne += " ·" + extras

            lignes.append(ligne)

        if not lignes:
            lignes.append(
                "Aucune opération journalisée pour "
                "le moment."
            )

        self.zone_texte.setPlainText(
            "\n".join(lignes)
        )

    def copier_tout(self):

        QApplication.clipboard().setText(
            self.zone_texte.toPlainText()
        )

    def copier_selection(self):

        texte = (
            self.zone_texte.textCursor().selectedText()
        )

        QApplication.clipboard().setText(texte)
