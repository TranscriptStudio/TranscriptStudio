from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
)


class EditWordDialog(QDialog):

    def __init__(
        self,
        word_text,
        parent=None
    ):
        super().__init__(parent)

        self.setWindowTitle(
            "Modifier le mot"
        )

        layout = QVBoxLayout(self)

        self.word_edit = QLineEdit(
            word_text
        )

        layout.addWidget(
            self.word_edit
        )

        buttons_layout = QHBoxLayout()

        self.validate_button = QPushButton(
            "Valider"
        )

        self.delete_button = QPushButton(
            "Supprimer"
        )

        self.cancel_button = QPushButton(
            "Annuler"
        )

        buttons_layout.addWidget(
            self.validate_button
        )

        buttons_layout.addWidget(
            self.delete_button
        )

        buttons_layout.addWidget(
            self.cancel_button
        )

        layout.addLayout(
            buttons_layout
        )

        self.validate_button.clicked.connect(
            self.accept
        )

        self.cancel_button.clicked.connect(
            self.reject
        )

        self.delete_requested = False

        self.delete_button.clicked.connect(
            self.request_delete
        )

    def request_delete(self):

        self.delete_requested = True

        self.accept()

    def get_text(self):

        return self.word_edit.text()