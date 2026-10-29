# ui/modifier_etude_dialog.py
"""
Mini-fenêtre « Modifier l'étude » (P18.6c, spec
navigation §4.1) : titre + thème, extensible.
"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)


class ModifierEtudeDialog(QDialog):
    """
    Titre et thème d'une étude.

    Le thème proposé en déroulant : « livre »
    (livre biblique) ou « libre » (thème libre).
    """

    def __init__(
        self,
        titre="",
        theme="livre",
        parent=None
    ):
        super().__init__(parent)

        self.setWindowTitle("Modifier l'étude")

        layout = QVBoxLayout(self)

        formulaire = QFormLayout()

        self.titre_edit = QLineEdit(titre or "")

        formulaire.addRow(
            "Titre de l'étude :",
            self.titre_edit
        )

        self.theme_combo = QComboBox()
        self.theme_combo.addItem(
            "Livre biblique",
            "livre"
        )
        self.theme_combo.addItem(
            "Thème libre",
            "libre"
        )

        index = self.theme_combo.findData(theme)

        if index >= 0:
            self.theme_combo.setCurrentIndex(
                index
            )

        formulaire.addRow(
            "Thème :",
            self.theme_combo
        )

        layout.addLayout(formulaire)

        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)

        layout.addWidget(boutons)

    def resultat(self):
        """
        (titre, theme) saisis.
        """

        return (
            self.titre_edit.text().strip(),
            self.theme_combo.currentData(),
        )
