# ui/sous_titres_dialog.py
"""
Dialogue de validation des sous-titres proposés
par IA (P20.2) : les suggestions du LLM sont
présentées ÉDITABLES, à valider une à une —
JAMAIS insérées automatiquement dans le document.

L'appelant (page Ouvrage) n'insère les sous-
titres retenus qu'après validation explicite de
ce dialogue.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class SousTitresDialog(QDialog):
    """
    Suggestions de sous-titres (P20.2) : chaque
    suggestion est une case à cocher + un champ
    éditable. ``suggestions_retenues()`` retourne
    les textes validés (édités), dans l'ordre.
    """

    def __init__(
        self,
        suggestions,
        titre_section: str = "",
        parent=None
    ):
        super().__init__(parent)

        self.setWindowTitle(
            "Sous-titres proposés par IA"
        )

        layout = QVBoxLayout(self)

        entete = QLabel(
            "Propositions de sous-titres pour la "
            "section"
            + (
                f" « {titre_section} »"
                if titre_section
                else ""
            )
            + " — cochez et éditez, puis validez :"
        )

        entete.setWordWrap(True)

        layout.addWidget(entete)

        self._lignes = []

        for suggestion in suggestions:

            ligne = QHBoxLayout()

            coche = QCheckBox()
            coche.setChecked(True)

            champ = QLineEdit(suggestion)

            ligne.addWidget(coche)
            ligne.addWidget(champ, stretch=1)

            layout.addLayout(ligne)

            self._lignes.append((coche, champ))

        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)

        layout.addWidget(boutons)

    def suggestions_retenues(self) -> list:
        """
        Les sous-titres validés (cochés, texte
        éventuellement édité), dans l'ordre.
        """

        retenues = []

        for coche, champ in self._lignes:

            if coche.isChecked():

                texte = champ.text().strip()

                if texte:
                    retenues.append(texte)

        return retenues
