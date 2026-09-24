from PySide6.QtWidgets import (
    QWidget
)

from PySide6.QtGui import (
    QPainter,
    QColor,
    QPalette,
)
from PySide6.QtCore import Signal, QRectF
ROW_HEIGHT = 23
HEADER_HEIGHT = 25

class TimelineSpeakerPanel(QWidget):
    # new_speaker_requested = Signal()
    rename_speaker_requested = Signal(
        str,  # speaker_id
        str   # speaker_name
    )
    def __init__(
        self,
        project,
        row_height=ROW_HEIGHT,
        parent=None
    ):
        super().__init__(parent)

        self.project = project

        self.row_height = row_height
        self.header_height = HEADER_HEIGHT

        self.setFixedWidth(120)

        self.setMinimumHeight(
            self.header_height
            + len(self.project.speakers)
            * self.row_height
            + 20
        )
        self.speaker_rects = []

    def paintEvent(self, event):
        self.speaker_rects.clear()
        painter = QPainter(self)

        for i, speaker in enumerate(
            self.project.speakers
        ):

            y = (self.header_height + i * self.row_height)
            block_y = y + 4
            block_height = self.row_height - 8

            center_y = block_y + block_height / 2

            painter.fillRect(
                10,
                int(center_y - 6),
                12,
                12,
                QColor(speaker.color)
            )

            text_color = self.palette().color(
                QPalette.ColorRole.Text
            )

            painter.setPen(
                text_color
            )

            painter.drawText(
                30,
                int(center_y + 5),
                speaker.name
            )
            rect = QRectF(
                0,
                y,
                self.width(),
                self.row_height
            )

            self.speaker_rects.append(
                (
                    rect,
                    speaker
                )
            )

    def mouseDoubleClickEvent(
        self,
        event
    ):

        pos = event.position()

        for rect, speaker in self.speaker_rects:

            if rect.contains(pos):

                self.rename_speaker_requested.emit(
                    speaker.id, 
                    speaker.name
                )

                return



        