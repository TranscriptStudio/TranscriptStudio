from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QPainterPath,

)
import numpy as np
from pathlib import Path
import wave

from services.audio_waveform_service import AudioWaveformService

class WaveformWidget(QWidget):

    def __init__(
        self,
        parent=None
    ):
        super().__init__(parent)

        self.document = None

        self.timeline_height = 25
  
   
        self.setMinimumHeight(250)
        self.dragging = False
        self.last_mouse_x = 0

    def format_time(
        self,
        seconds
    ):
        total = int(seconds)

        hours = total // 3600

        minutes = (
            total % 3600
        ) // 60

        secs = total % 60

        if hours > 0:
            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{secs:02d}"
            )

        return (
            f"{minutes:02d}:"
            f"{secs:02d}"
        )

    def paintEvent(
        self,
        event
    ):
        painter = QPainter(self)

        painter.fillRect(
            self.rect(),
            QColor("white")
        )

        if (
            self.document is None
            or self.document.waveform is None
        ):
            return

        visible_samples, start, end = (
            self.get_visible_samples()
        )
        total_samples = len(
            self.document.waveform
        )
        visible_start_time = (
            start
            / total_samples
            * self.document.duration_seconds
        )

        visible_end_time = (
            end
            / total_samples
            * self.document.duration_seconds
        )
        mins, maxs = (
            self.build_waveform_envelope(
                visible_samples
            )
        )


        if len(visible_samples) == 0:
            return  

        timeline_height = (
            self.timeline_height
        )

        waveform_top = (
            timeline_height
        )

        waveform_height = (
            self.height()
            - timeline_height
        )

        center_y = (
            waveform_top
            + waveform_height / 2
        )

        pen = QPen(
            QColor("#4A90E2")
        )

        painter.setPen(pen)

        width = self.width()

        if self.document.duration_seconds > 0:

            painter.setPen(
                QColor("#A0A0A0")
            )

            painter.drawLine(
                0,
                timeline_height - 5,
                width,
                timeline_height - 5
            )

            visible_duration = (
                visible_end_time
                - visible_start_time
            )

            step_seconds = (
                self.get_adaptive_step(
                    visible_duration
                )
            )

            current = (
                int(
                    visible_start_time
                    / step_seconds
                )
                * step_seconds
            )

            while current <= visible_end_time:

                x = (
                    (
                        current
                        - visible_start_time
                    )
                    / visible_duration
                ) * width

                painter.drawLine(
                    int(x),
                    timeline_height - 12,
                    int(x),
                    timeline_height - 2
                )

                painter.drawText(
                    int(x) + 2,
                    12,
                    self.format_time(
                        current
                    )
                )

                current += step_seconds

        

        for x in range(len(mins)):

            y_min = (
                center_y
                - maxs[x]
                * (waveform_height / 2)
            )

            y_max = (
                center_y
                - mins[x]
                * (waveform_height / 2)
            )

            painter.drawLine(
                x,
                int(y_min),
                x,
                int(y_max)
            )

    def load_audio(
        self,
        audio_file
    ):

        document = (
            AudioWaveformService()
            .extract_waveform(
                audio_file
            )
        )

        self.set_document(
            document
        )

    def set_document(
        self,
        document
    ):
        self.document = document
        self.update()

    def zoom_in(self):

        if self.document is None:
            return

        self.document.zoom_factor *= 1.5

        if self.document.zoom_factor > 1000:
            self.document.zoom_factor = 1000

        self.update()

    def zoom_out(self):

        if self.document is None:
            return

        self.document.zoom_factor /= 1.5

        if self.document.zoom_factor < 1:
            self.document.zoom_factor = 1

        self.update()

    def fit_all(self):

        if self.document is None:
            return

        self.document.zoom_factor = 1

        self.document.view_offset = 0

        self.update()

    def get_visible_samples(self):

        waveform = self.document.waveform

        total_samples = len(waveform)

        visible_samples = int(
            total_samples
            / self.document.zoom_factor
        )

        visible_samples = max(
            50,
            visible_samples
        )

        max_offset = max(
            0,
            total_samples - visible_samples
        )

        start = int(
            self.document.view_offset
            * max_offset
        )

        end = min(
            total_samples,
            start + visible_samples
        )

        visible = waveform[start:end]

        return (
            visible,
            start,
            end
        )

    def build_waveform_envelope(
        self,
        samples
    ):

        pixel_width = max(
            1,
            self.width()*3
        )

        if len(samples) <= pixel_width:

            mins = samples.copy()
            maxs = samples.copy()

            return mins, maxs

        samples_per_pixel = (
            len(samples)
            / pixel_width
        )

        mins = []
        maxs = []

        for x in range(pixel_width):

            start = int(
                x * samples_per_pixel
            )

            end = int(
                (x + 1)
                * samples_per_pixel
            )

            if end <= start:
                end = start + 1

            chunk = samples[start:end]

            mins.append(
                np.min(chunk)
            )

            maxs.append(
                np.max(chunk)
            )

        return (
            np.array(mins),
            np.array(maxs)
        )

    def get_adaptive_step(
        self,
        visible_duration
    ):    

        if visible_duration > 3600:
            return 600

        if visible_duration > 1800:
            return 300

        if visible_duration > 600:
            return 60

        if visible_duration > 120:
            return 30

        if visible_duration > 30:
            return 10

        if visible_duration > 10:
            return 5

        return 1

    def wheelEvent(self, event):

        if self.document is None:
            return

        mouse_ratio = (
            event.position().x()
            / max(1, self.width())
        )

        old_zoom = self.document.zoom_factor

        if event.angleDelta().y() > 0:
            self.document.zoom_factor *= 1.2
        else:
            self.document.zoom_factor /= 1.2

        self.document.zoom_factor = max(
            1,
            min(100, self.document.zoom_factor)
        )

        zoom_change = (
            old_zoom
            / self.document.zoom_factor
        )

        self.document.view_offset += (
            mouse_ratio
            * (1 - zoom_change)
        )

        self.document.view_offset = max(
            0.0,
            min(1.0, self.document.view_offset)
        )

        self.update()

    def mousePressEvent(self, event):

        self.dragging = True

        self.last_mouse_x = (
            event.position().x()
        )

    def mouseMoveEvent(self, event):

        if (
            not self.dragging
            or self.document is None
        ):
            return

        delta_x = (
            event.position().x()
            - self.last_mouse_x
        )

        self.last_mouse_x = (
            event.position().x()
        )

        self.document.view_offset -= (
            delta_x
            / self.width()
            / self.document.zoom_factor
        )

        self.document.view_offset = max(
            0.0,
            min(
                1.0,
                self.document.view_offset
            )
        )

        self.update()

    def mouseReleaseEvent(self, event):

        self.dragging = False




        