from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGroupBox,
    QRadioButton,
    QCheckBox,
    QPushButton,
)


class ExportDialog(QDialog):

    def __init__(self, project, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            "Exporter"
        )
        self.project = project
        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        #
        # Format
        #
        format_group = QGroupBox(
            "Format"
        )

        format_layout = QVBoxLayout()

        self.txt_radio = QRadioButton(
            "TXT"
        )

        self.json_radio = QRadioButton(
            "JSON"
        )

        self.docx_radio = QRadioButton(
            "DOCX"
        )

        self.pdf_radio = QRadioButton(
            "PDF"
        )

        self.txt_radio.setChecked(True)

        format_layout.addWidget(
            self.txt_radio
        )

        format_layout.addWidget(
            self.json_radio
        )

        format_layout.addWidget(
            self.docx_radio
        )

        format_layout.addWidget(
            self.pdf_radio
        )

        format_group.setLayout(
            format_layout
        )

        layout.addWidget(
            format_group
        )

        #
        # Options
        #
        self.speakers_checkbox = QCheckBox(
            "Afficher les intervenants"
        )

        self.speakers_checkbox.setChecked(True)

        self.timestamps_checkbox = QCheckBox(
            "Afficher les horodatages"
        )

        if not self.project.is_diarized:

            self.speakers_checkbox.setEnabled(False)

            self.speakers_checkbox.setChecked(False)

        layout.addWidget(
            self.speakers_checkbox
        )

        layout.addWidget(
            self.timestamps_checkbox
        )

        #
        # Bouton
        #
        self.export_button = QPushButton(
            "Exporter"
        )

        self.export_button.clicked.connect(
            self.accept
        )

        layout.addWidget(
            self.export_button
        )

    def get_options(self):

        fmt = "txt"

        if self.json_radio.isChecked():
            fmt = "json"

        elif self.docx_radio.isChecked():
            fmt = "docx"

        elif self.pdf_radio.isChecked():
            fmt = "pdf"

        return {

            "format": fmt,

            "include_speakers":
                self.speakers_checkbox.isChecked(),

            "include_timestamps":
                self.timestamps_checkbox.isChecked()

        }