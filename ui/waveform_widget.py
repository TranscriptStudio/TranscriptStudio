# ui/waveform_widget.py

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QPainterPath,
    QCursor,

)
from PySide6.QtCore import Signal, Qt,QUrl

import numpy as np



from services.audio_waveform_service import AudioWaveformService

class WaveformWidget(QWidget):

    seek_requested = Signal(float)

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

        self.dragging_trim_start = False
        self.dragging_trim_end = False

        self.trim_start_x = None
        self.trim_end_x = None
        self.setMouseTracking(
            True
        )

    def format_time(
        self,
        seconds,
        precise=False
    ):
        total = int(seconds)

        hours = total // 3600

        minutes = (
            total % 3600
        ) // 60

        secs = total % 60

        if precise:

            tenth = int(
                (seconds - total) * 10
            )

            if hours > 0:
                return (
                    f"{hours:02d}:"
                    f"{minutes:02d}:"
                    f"{secs:02d}."
                    f"{tenth}"
                )

            return (
                f"{minutes:02d}:"
                f"{secs:02d}."
                f"{tenth}"
            )

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

        self.visible_start_time = (
            visible_start_time
        )

        self.visible_end_time = (
            visible_end_time
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
            QColor("#2A7DDC")
        )
        pen.setWidth(1)

        painter.setPen(pen)

        width = self.width()

        self.draw_timeline(
            painter,
            width,
            timeline_height,
            visible_start_time,
            visible_end_time
        )

        self.draw_waveform(
            painter,
            mins,
            maxs,
            center_y,
            waveform_height
        )       
        self.draw_trim_overlay(
            painter,
            width,
            timeline_height,
        )
        self.draw_silence_overlay(
            painter,
            width,
            timeline_height,
        )
        cursor_x = self.draw_playback_cursor(
            painter,
            width,
            timeline_height,
            visible_start_time,
            visible_end_time
        )

        self.draw_time_bubble(
            painter,
            cursor_x,
            width
        )

    def draw_timeline(
        self,
        painter,
        width,
        timeline_height,
        visible_start_time,
        visible_end_time
    ):
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
        
                        show_precise = (
                            visible_duration < 30
                        )
        
                        painter.drawText(
                            int(x) + 2,
                            12,
                            self.format_time(
                                current,
                                show_precise
                            )
                        )
        
                        current += step_seconds

    def draw_waveform(
        self,
        painter,
        mins,
        maxs,
        center_y,
        waveform_height
    ):
    
        painter.setPen(
            QColor("#4A90E2")
        )
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

            # if y_max - y_min > 1:

            #     painter.drawLine(
            #         x + 1,
            #         int(y_min),
            #         x + 1,
            #         int(y_max)
            #     )

    def draw_trim_overlay(
        self,
        painter,
        width,
        timeline_height,
    ):

        parent_dialog = self.parent()

        while (
            parent_dialog
            and not hasattr(
                parent_dialog,
                "settings"
            )
        ):
            parent_dialog = parent_dialog.parent()

        if parent_dialog is None:
            return

        settings = parent_dialog.settings

        if not settings.trim_start_enabled:
            return

        visible_duration = (
            self.visible_end_time
            - self.visible_start_time
        )

        if visible_duration <= 0:
            return

        start_ratio = (
            settings.trim_start_time
            - self.visible_start_time
        ) / visible_duration

        end_ratio = (
            settings.trim_end_time
            - self.visible_start_time
        ) / visible_duration

        start_x = start_ratio * width
        end_x = end_ratio * width

        start_x = max(
            0,
            min(width, start_x)
        )

        end_x = max(
            0,
            min(width, end_x)
        )

        self.trim_start_x = start_x
        self.trim_end_x = end_x

        overlay_color = QColor(
            46,
            204,
            113,
            110
        )

        painter.fillRect(
            0,
            timeline_height,
            int(max(0, start_x)),
            self.height() - timeline_height,
            overlay_color
        )

        painter.fillRect(
            int(max(0, end_x)),
            timeline_height,
            width,
            self.height() - timeline_height,
            overlay_color
        )

        handle_color = QColor(
            "#1E8449"
        )

        painter.setPen(
            QPen(
                handle_color,
                2
            )
        )

        painter.drawLine(
            int(start_x),
            timeline_height,
            int(start_x),
            self.height()
        )

        painter.drawLine(
            int(end_x),
            timeline_height,
            int(end_x),
            self.height()
        )

        painter.setBrush(
            handle_color
        )

        painter.setPen(
            Qt.NoPen
        )

        start_triangle = [
            (start_x, timeline_height),
            (start_x - 8, timeline_height - 12),
            (start_x + 8, timeline_height - 12),
        ]

        end_triangle = [
            (end_x, timeline_height),
            (end_x - 8, timeline_height - 12),
            (end_x + 8, timeline_height - 12),
        ]

        from PySide6.QtCore import QPoint

        painter.drawPolygon(
            [
                QPoint(
                    int(x),
                    int(y)
                )
                for x, y in start_triangle
            ]
        )

        painter.drawPolygon(
            [
                QPoint(
                    int(x),
                    int(y)
                )
                for x, y in end_triangle
            ]
        )
    def draw_silence_overlay(
        self,
        painter,
        width,
        timeline_height,
    ):

        parent_dialog = self.parent()

        while (
            parent_dialog
            and not hasattr(
                parent_dialog,
                "settings"
            )
        ):
            parent_dialog = parent_dialog.parent()

        if parent_dialog is None:
            return

        settings = parent_dialog.settings

        if not settings.silence_enabled:
            return

        if not hasattr(
            parent_dialog,
            "detected_silences"
        ):
            return

        visible_duration = (
            self.visible_end_time
            - self.visible_start_time
        )

        if visible_duration <= 0:
            return

        silence_color = QColor(
            106,
            27,
            154,
            110
        )

        for start_time, end_time in (
            parent_dialog.filtered_silences
        ):

            start_ratio = (
                start_time
                - self.visible_start_time
            ) / visible_duration

            end_ratio = (
                end_time
                - self.visible_start_time
            ) / visible_duration

            start_x = (
                start_ratio
                * width
            )

            end_x = (
                end_ratio
                * width
            )

            start_x = max(
                0,
                min(width, start_x)
            )

            end_x = max(
                0,
                min(width, end_x)
            )

            if end_x <= start_x:
                continue

            painter.fillRect(
                int(start_x),
                timeline_height,
                int(end_x - start_x),
                self.height() - timeline_height,
                silence_color
            )
    def draw_playback_cursor(
        self,
        painter,
        width,
        timeline_height,
        visible_start_time,
        visible_end_time
    ):
        current_time = (
            self.document.current_time
        )

        if visible_end_time > visible_start_time:

            ratio = (
                (
                    current_time
                    - visible_start_time
                )
                /
                (
                    visible_end_time
                    - visible_start_time
                )
            )

            ratio = max(
                0.0,
                min(
                    1.0,
                    ratio
                )
            )

            cursor_x = ratio * width

        painter.setPen(
            QPen(
                QColor("red"),
                2
            )
        )

        painter.drawLine(
            int(cursor_x),
            timeline_height,
            int(cursor_x),
            self.height()
        )

        painter.setBrush(
            QColor("#FF5252")
        )

        painter.setPen(
            Qt.NoPen
        )

        painter.drawEllipse(
            int(cursor_x) - 5,
            timeline_height - 5,
            10,
            10
        )
        return cursor_x

    def draw_time_bubble(
        self,
        painter,
        cursor_x,
        width
    ):
        
        time_text = self.format_time(
            self.document.current_time
        )
        bubble_width = 70
        bubble_height = 22

        bubble_x = (
            cursor_x
            - bubble_width / 2
        )

        bubble_x = max(
            0,
            bubble_x
        )

        bubble_x = min(
            width - bubble_width,
            bubble_x
        )
        bubble_y = (
            self.timeline_height + 5
        )

        painter.setPen(
            Qt.NoPen
        )

        painter.setBrush(
            QColor("#29292D")
        )

        painter.drawRoundedRect(
            int(bubble_x),
            int(bubble_y),
            bubble_width,
            bubble_height,
            6,
            6
        )

        painter.setPen(
            QColor("white")
        )

        rect = (
            int(bubble_x),
            int(bubble_y),
            bubble_width,
            bubble_height
        )

        painter.drawText(
            rect[0],
            rect[1],
            rect[2],
            rect[3],
            Qt.AlignCenter,
            time_text
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

        if self.document.zoom_factor > 10000:
            self.document.zoom_factor = 10000

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

    def get_visible_ratio(self):

        total_samples = len(
            self.document.waveform
        )

        visible_samples = int(
            total_samples
            / self.document.zoom_factor
        )

        visible_samples = max(
            50,
            visible_samples
        )

        return (
            visible_samples
            / total_samples
        )

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
            self.width()
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

        old_visible_ratio = (
            self.get_visible_ratio()
        )

        center_ratio = (
            self.document.view_offset
            + old_visible_ratio / 2
        )

        if event.angleDelta().y() > 0:
            self.document.zoom_factor *= 1.2
        else:
            self.document.zoom_factor /= 1.2

        self.document.zoom_factor = max(
            1,
            min(
                10000,
                self.document.zoom_factor
            )
        )

        new_visible_ratio = (
            self.get_visible_ratio()
        )

        self.document.view_offset = (
            center_ratio
            - new_visible_ratio / 2
        )

        self.document.view_offset = max(
            0.0,
            min(
                1.0 - new_visible_ratio,
                self.document.view_offset
            )
        )
        

        self.update()

    def is_over_trim_start(
        self,
        x
    ):
        if self.trim_start_x is None:
            return False

        return abs(
            x - self.trim_start_x
        ) <= 10


    def is_over_trim_end(
        self,
        x
    ):
        if self.trim_end_x is None:
            return False

        return abs(
            x - self.trim_end_x
        ) <= 10

    def mousePressEvent(self, event):

        if self.document is None:
            return

        x = event.position().x()

        if self.is_over_trim_start(x):

            self.dragging_trim_end = False
            self.dragging_trim_start = True

            self.update_cursor(
                x
            )

            return

        if self.is_over_trim_end(x):

            self.dragging_trim_start = False
            self.dragging_trim_end = True

            self.update_cursor(
                x
            )

            return

        self.dragging = True

        self.last_mouse_x = x

    def mouseMoveEvent(self, event):

        if self.document is None:
            return
        x = event.position().x()

        self.update_cursor(x)

        parent_dialog = self.parent()

        while (
            parent_dialog
            and not hasattr(
                parent_dialog,
                "settings"
            )
        ):
            parent_dialog = parent_dialog.parent()

        if parent_dialog:

            settings = parent_dialog.settings

            visible_duration = (
                self.visible_end_time
                - self.visible_start_time
            )

            if self.dragging_trim_start:

                ratio = (
                    event.position().x()
                    / self.width()
                )

                new_time = (
                    self.visible_start_time
                    + ratio
                    * visible_duration
                )

                settings.trim_start_time = max(
                    0.0,
                    min(
                        new_time,
                        settings.trim_end_time
                    )
                )

                parent_dialog.trim_start_edit.setText(
                    parent_dialog.format_time_tenth(
                        settings.trim_start_time
                    )
                )

                parent_dialog.on_trim_changed()

                self.update()

                return

            if self.dragging_trim_end:

                ratio = (
                    event.position().x()
                    / self.width()
                )

                new_time = (
                    self.visible_start_time
                    + ratio
                    * visible_duration
                )

                settings.trim_end_time = max(
                    settings.trim_start_time,
                    min(
                        new_time,
                        self.document.duration_seconds
                    )
                )

                parent_dialog.trim_end_edit.setText(
                    parent_dialog.format_time_tenth(
                        settings.trim_end_time
                    )
                )

                parent_dialog.on_trim_changed()

                self.update()

                return

        if not self.dragging:
            return

        dx = (
            event.position().x()
            - self.last_mouse_x
        )

        self.last_mouse_x = (
            event.position().x()
        )
        move_ratio = (
            dx
            / self.width()
        )
        visible_ratio = (
            self.get_visible_ratio()
        )

        self.document.view_offset -= (
            dx
            / self.width()
            * visible_ratio
        )

        self.document.view_offset = max(
            0.0,
            min(
                1.0 - visible_ratio,
                self.document.view_offset
            )
        )

        self.update()

    def mouseReleaseEvent(self, event):

        self.dragging = False

        self.dragging_trim_start = False
        self.dragging_trim_end = False

        mouse_pos = event.position().x()

        self.update_cursor(
            mouse_pos
        )
        self.repaint()
        super().mouseReleaseEvent(
            event
        )

    def mouseDoubleClickEvent(
        self,
        event
    ):
        ratio = (
            event.position().x()
            / self.width()
        )

        visible_duration = (
            self.visible_end_time
            - self.visible_start_time
        )

        target_time = (
            self.visible_start_time
            + ratio
            * visible_duration
        )
        self.document.disable_auto_follow = True
        self.seek_requested.emit(
            target_time
        )

    def update_cursor(self, x):

        if (
            self.dragging_trim_start
            or self.dragging_trim_end
        ):
            self.setCursor(
                Qt.ClosedHandCursor
            )
            return

        if (
            self.is_over_trim_start(x)
            or self.is_over_trim_end(x)
        ):
            self.setCursor(
                Qt.OpenHandCursor
            )
        else:
            self.setCursor(
                Qt.ArrowCursor
            )

    def leaveEvent(
        self,
        event
    ):

        self.setCursor(
            Qt.ArrowCursor
        )

        super().leaveEvent(
            event
        )
            
        