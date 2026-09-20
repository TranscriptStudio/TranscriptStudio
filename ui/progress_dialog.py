from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
)

from PySide6.QtCore import (
    QTimer
)


class ProgressDialog(QDialog):

    def __init__(
        self,
        audio_file,
        parent=None
    ):
        super().__init__(parent)

        self.elapsed = 0

        self.setWindowTitle(
            "Transcription"
        )

        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                f"Audio : {audio_file}"
            )
        )

        layout.addWidget(
            QLabel(
                "Transcription en cours..."
            )
        )

        self.timer_label = QLabel(
            "00:00"
        )

        layout.addWidget(
            self.timer_label
        )

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update_time
        )

        self.timer.start(1000)

    def update_time(self):

        self.elapsed += 1

        m = self.elapsed // 60
        s = self.elapsed % 60

        self.timer_label.setText(
            f"Temps écoulé : {m:02}:{s:02}"
        )