# ui/ouvrage_window.py
"""
Page Ouvrage (P18.6, spec navigation §4-§5) :
l'assemblage et l'export final de l'ouvrage se
font ICI — la page Étude y renvoie.

La mécanique complète (arborescence à la Word,
document compilé éditable, rapport d'analyse,
fusion de pensées, mobilité des paragraphes,
sous-titres IA) reste définie par P19/P20 de la
feuille de route : cette page en pose la
destination de navigation et porte l'export
final (P18.3) en attendant.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from services.etude_io import EtudeOuverte
from services.help import open_user_manual
from services.settings import SettingsManager


class OuvrageWindow(QWidget):
    """
    Page Ouvrage d'une étude : export final de
    l'ouvrage (P18.3) — la présentation complète
    arrive avec P19/P20.
    """

    def __init__(
        self,
        etude: EtudeOuverte,
        settings=None
    ):
        super().__init__()

        self.etude = etude

        self.settings = (
            settings
            if settings is not None
            else SettingsManager()
        )

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        #
        # Ruban (même langage que la page Réunion).
        #
        ruban = QWidget()
        ruban.setObjectName("ruban_ouvrage")

        ruban_layout = QHBoxLayout(ruban)
        ruban_layout.setContentsMargins(0, 0, 0, 0)
        ruban_layout.setSpacing(10)

        titre = QLabel(
            "Ouvrage — "
            + (self.etude.etude.titre or "Étude")
        )
        titre.setStyleSheet(
            "font-size: 18px; font-weight: 600;"
        )

        ruban_layout.addWidget(titre)
        ruban_layout.addStretch()

        self.etude_button = QPushButton(
            "Gestion de l'étude"
        )
        self.etude_button.setToolTip(
            "Ouvrir la page Étude (réunions, "
            "synthèse, paramètres de l'étude)"
        )
        self.etude_button.clicked.connect(
            self.ouvrir_etude
        )

        self.accueil_button = QPushButton(
            "Accueil"
        )
        self.accueil_button.clicked.connect(
            self.ouvrir_accueil
        )

        self.parametres_button = QPushButton(
            "⚙ Paramètres"
        )
        self.parametres_button.clicked.connect(
            self.ouvrir_parametres
        )

        self.aide_button = QPushButton("? Aide")
        self.aide_button.clicked.connect(
            open_user_manual
        )

        for bouton in (
            self.etude_button,
            self.accueil_button,
            self.parametres_button,
            self.aide_button,
        ):
            ruban_layout.addWidget(bouton)

        layout.addWidget(ruban)

        #
        # Contenu : destination P19/P20 + export
        # final (P18.3).
        #
        note = QLabel(
            "Le document ouvrage (arborescence des "
            "chapitres, document compilé éditable, "
            "rapport d'analyse, fusion de pensées) "
            "arrive avec la page Ouvrage complète "
            "(P19/P20).\n\n"
            "En attendant, l'assemblage et l'export "
            "final des textes validés se font ici."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #555555;")

        layout.addWidget(note)
        layout.addSpacing(6)

        apercu = QPlainTextEdit()
        apercu.setReadOnly(True)
        apercu.setPlaceholderText(
            "Aperçu de l'assemblage : "
            "« Exporter l'ouvrage… » propose un "
            "aperçu avant génération."
        )
        apercu.setMaximumHeight(160)

        layout.addWidget(apercu)
        layout.addSpacing(6)

        actions = QHBoxLayout()

        self.exporter_button = QPushButton(
            "📤 Exporter l'ouvrage…"
        )
        self.exporter_button.setToolTip(
            "Assembler les textes validés (résumés en "
            "tête de section, reformulations dans "
            "l'ordre d'ouvrage) et exporter en "
            "document Word ou texte — export final "
            "de l'étude"
        )
        self.exporter_button.clicked.connect(
            self.exporter_ouvrage
        )

        actions.addWidget(self.exporter_button)
        actions.addStretch()

        layout.addLayout(actions)
        layout.addStretch()

    # ==================================================
    # Navigation.
    # ==================================================

    def ouvrir_etude(self):

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if navigation is not None:
            navigation.ouvrir_etude(
                self.etude.dossier
            )

    def ouvrir_accueil(self):

        navigation = getattr(
            self,
            "navigation",
            None
        )

        if navigation is not None:
            navigation.ouvrir_accueil()

    def ouvrir_parametres(self):

        from ui.settings_dialog import SettingsDialog

        dialogue = SettingsDialog(
            self,
            settings=self.settings
        )

        if dialogue.exec():
            self.settings.load()

    # ==================================================
    # Export final (P18.3).
    # ==================================================

    def exporter_ouvrage(self):
        """
        « Exporter l'ouvrage… » : assemble les
        textes validés (résumés en tête de section
        si souhaité, reformulations dans l'ordre
        d'ouvrage) et exporte en DOCX (ou TXT).
        Flux P13 : message de fin avec ouverture du
        fichier ou du dossier.
        """

        import re as _re

        from services.export_ouvrage import (
            assembler_ouvrage,
            exporter_docx,
            exporter_txt,
        )

        apercu = assembler_ouvrage(
            self.etude,
            inclure_resumes=True,
            en_tetes_reunions=True
        )

        if not apercu["reunions"]:

            QMessageBox.information(
                self,
                "Rien à exporter",
                (
                    "Aucun texte validé dans l'étude : "
                    "validez des reformulations (ou un "
                    "résumé) avant d'exporter l'ouvrage."
                )
            )

            return

        dialogue = QDialog(self)
        dialogue.setWindowTitle("Exporter l'ouvrage")

        options = QVBoxLayout(dialogue)

        resumes_check = QCheckBox(
            "Inclure les résumés validés "
            "en tête de section"
        )
        resumes_check.setChecked(True)

        tetes_check = QCheckBox(
            "Titres de réunion"
        )
        tetes_check.setChecked(True)

        options.addWidget(resumes_check)
        options.addWidget(tetes_check)

        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        boutons.accepted.connect(dialogue.accept)
        boutons.rejected.connect(dialogue.reject)

        options.addWidget(boutons)

        if dialogue.exec() != (
            QDialog.DialogCode.Accepted
        ):
            return

        nom_defaut = _re.sub(
            r"[^\w\- ]",
            "",
            apercu["titre"]
        ).strip() or "ouvrage"

        chemin, filtre = QFileDialog.getSaveFileName(
            self,
            "Exporter l'ouvrage",
            str(
                self.etude.dossier
                / f"{nom_defaut}.docx"
            ),
            "Document Word (*.docx);;"
            "Texte (*.txt)"
        )

        if not chemin:
            return

        ouvrage = assembler_ouvrage(
            self.etude,
            inclure_resumes=(
                resumes_check.isChecked()
            ),
            en_tetes_reunions=(
                tetes_check.isChecked()
            )
        )

        try:

            if filtre.startswith("Document"):
                chemin = exporter_docx(
                    ouvrage,
                    chemin
                )
            else:
                chemin = exporter_txt(
                    ouvrage,
                    chemin
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Export impossible",
                str(e)
            )

            return

        message = QMessageBox(self)
        message.setWindowTitle("Ouvrage exporté")
        message.setText(
            f"L'ouvrage a été exporté :\n\n{chemin}"
        )

        open_file_button = message.addButton(
            "Ouvrir le fichier",
            QMessageBox.ButtonRole.AcceptRole
        )

        open_folder_button = message.addButton(
            "Ouvrir le dossier",
            QMessageBox.ButtonRole.AcceptRole
        )

        message.addButton(
            "Fermer",
            QMessageBox.ButtonRole.RejectRole
        )

        message.exec()

        clicked = message.clickedButton()

        if clicked is open_file_button:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(chemin))
            )

        elif clicked is open_folder_button:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(Path(chemin).parent)
                )
            )
