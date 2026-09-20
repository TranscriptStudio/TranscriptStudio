from PySide6.QtWidgets import (
    QWidget,
    QMenu,
)

from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush
)

from PySide6.QtCore import Qt, QRectF, Signal
ROW_HEIGHT = 23

HEADER_HEIGHT = 25

class TimelineWidget(QWidget):

    seek_requested = Signal(float)

    block_clicked = Signal(int)
    new_speaker_requested = Signal()
    speaker_change_requested = Signal(
        int,   # block_id
        str    # speaker_id
    )

    def __init__(
        self,
        project,
        parent=None
    ):
        super().__init__(parent)

        self.project = project

        self.current_time = 0.0
        self.duration = 0
        
        self.zoom = 1.0

        self.row_height = ROW_HEIGHT

        height = (
            len(project.speakers)
            * self.row_height
            + 20
        )

        self.setMinimumHeight(height)
        self.setMinimumWidth(1000)

        self.setStyleSheet("""
        background:#EEEEEE;
        """)

        self.header_height = 25
        self.zoom = 1.0
        self.fit_zoom = None
        self.min_zoom = 0.01
        self.max_zoom = 20.0
        self.base_pixels_per_second = 1.0
        self.zoom_fit()
        self.block_rects = []
        self.timeline_scroll = None
        
    def set_current_time(
        self,
        time_seconds
    ):

        self.current_time = time_seconds

        self.ensure_cursor_visible()

        self.update()
        
    def set_zoom(self, zoom):

        self.zoom = max(
            self.min_zoom,
            min(
                zoom,
                self.max_zoom
            )
        )

        self.update_timeline_width()

        # self.update()

    def zoom_in(self):

        self.zoom = min(
            self.zoom * 1.5,
            self.max_zoom
        )

        self.update_timeline_width()

    def zoom_out(self):

        fit_zoom = self.get_fit_zoom()

        new_zoom = self.zoom / 1.5

        self.zoom = max(
            new_zoom,
            fit_zoom
        )

        self.update_timeline_width()

    def get_fit_zoom(self):

        duration = self.get_duration()

        if duration <= 0:
            return 1.0

        viewport = self.parent()

        while viewport and not hasattr(
            viewport,
            "viewport"
        ):
            viewport = viewport.parent()

        visible_width = (
            viewport.viewport().width()
            if viewport
            else 1000
        )

        return (
            visible_width * 0.85
        ) / duration

    def zoom_fit(self):

        self.zoom = self.get_fit_zoom()

        self.update_timeline_width()

    def get_duration(self):

        if not self.project.words:
            return 1

        last_word = self.project.words[-1]

        return (
            last_word.end
            if last_word.end
            else 1
        )

    def paintEvent(
        self,
        event
    ):

        painter = QPainter(self)
        

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        duration = self.get_duration()

        timeline_width = self.width()

        #
        # Correspondance speaker -> ligne
        #
        speaker_rows = {}

        #
        # Fond
        #
        painter.fillRect(
            self.rect(),
            QColor("#F8F8F8")
        )

        self.header_height = HEADER_HEIGHT

        block_height =  self.row_height - 8
        #
        # Axe temporel
        #
        painter.setPen(
            QColor("#888888")
        )

        duration = self.get_duration()

        timeline_width = self.width()

        step_seconds = self.get_time_step()

        current = 0

        while current <= duration:

            x = (
                current
                / duration
            ) * timeline_width

            #
            # Graduation
            #
            painter.drawLine(
                int(x),
                self.header_height - 8,
                int(x),
                self.header_height
            )

            #
            # Texte
            #
            minutes = current // 60

            seconds = current % 60

            if duration >= 3600:

                hours = current // 3600

                minutes = (
                    current % 3600
                ) // 60

                label = (
                    f"{int(hours):02}:{int(minutes):02}"
                )

            else:

                minutes = current // 60

                seconds = current % 60

                label = (
                    f"{int(minutes):02}:{int(seconds):02}"
                )

            painter.drawText(
                int(x) + 2,
                self.header_height - 10,
                label
            )

            current += step_seconds

        #
        # Ligne séparatrice sous l'axe
        #
        painter.setPen(
            QColor("#D0D0D0")
        )

        painter.drawLine(
            0,
            self.header_height,
            self.width(),
            self.header_height
        )
        #
        # Grille horizontale
        #
        painter.setPen(
            QColor("#E0E0E0")
        )

        for row in range(
            len(self.project.speakers) + 1
        ):

            y = self.header_height + (row * self.row_height)

            painter.drawLine(
                0,
                y,
                self.width(),
                y
            )
        for index, speaker in enumerate(
            self.project.speakers
        ):

            speaker_rows[
                speaker.id
            ] = index
        #
        # Blocs de parole
        #
        self.block_rects.clear()

        for block in self.project.blocks:

            try:

                start_word = (
                    self.project.words[
                        block.start_word
                    ]
                )

                end_word = (
                    self.project.words[
                        block.end_word
                    ]
                )

            except Exception:
                continue

            if (
                start_word.start is None
                or end_word.end is None
            ):
                continue

            start = start_word.start
            end = end_word.end

            block_duration = (
                end - start
            )

            x = (
                start
                / duration
            ) * timeline_width

            w = max(
                (
                    block_duration
                    / duration
                ) * timeline_width,
                6
            )

            row = speaker_rows.get(
                block.speaker_id,
                0
            )

            y = (
                self.header_height
                + row * self.row_height
            ) + 4


            speaker = (
                self.project.get_speaker_by_id(
                    block.speaker_id
                )
            )

            color = QColor(
                speaker.color
            )

            painter.setBrush(
                QBrush(color)
            )

            painter.setPen(
                Qt.PenStyle.NoPen
            )
            
           

            painter.drawRoundedRect(
                QRectF(
                    x,
                    y,
                    w,
                    block_height
                ),
                5,
                5
            )
            self.block_rects.append(
                (
                    QRectF(
                        x,
                        y,
                        w,
                        block_height
                    ),
                    block
                )
            )
            
        #
        # Curseur de lecture
        #
        cursor_x = (
            self.current_time
            / duration
        ) * timeline_width

        

        #
        # Texte temps
        #
        total_seconds = int(self.current_time)

        hours = total_seconds // 3600

        minutes = (
            total_seconds % 3600
        ) // 60

        seconds = (
            total_seconds % 60
        )

        if hours > 0:

            time_text = (
                f"{hours:02}:{minutes:02}:{seconds:02}"
            )

        else:

            time_text = (
                f"{minutes:02}:{seconds:02}"
            )
        #
        # Taille bulle
        #
        metrics = painter.fontMetrics()

        text_width = (
            metrics.horizontalAdvance(
                time_text
            )
        )

        bubble_width = (
            text_width + 12
        )

        bubble_height = 22
        bubble_x = (
            cursor_x
            - bubble_width / 2
        )

        bubble_y = 4

        painter.setPen(
            Qt.PenStyle.NoPen
        )

        painter.setBrush(
            QColor("#333333")
        )

        self.cursor_rect = QRectF(
            bubble_x,
            bubble_y,
            bubble_width,
            bubble_height
        )

        painter.drawRoundedRect(
            self.cursor_rect,
            6,
            6
        )

        painter.setPen(
            QColor("white")
        )

        painter.drawText(
            QRectF(
                bubble_x,
                bubble_y,
                bubble_width,
                bubble_height
            ),
            Qt.AlignmentFlag.AlignCenter,
            time_text
        )
        painter.setPen(
            QPen(
                QColor(255, 19, 11, 140),
                1
            )
        )


        painter.drawLine(
            int(cursor_x),
            self.header_height,
            int(cursor_x),
            self.height()
        )   
 
    def mousePressEvent(self, event):

        click_pos = event.position()

        hit_rect = self.cursor_rect.adjusted(
            -8,
            -8,
            8,
            8
        )

        if hit_rect.contains(click_pos):

            self.dragging_cursor = True

            return

        duration = self.get_duration()

        if duration <= 0:
            return

        ratio = (
            click_pos.x()
            / self.width()
        )

        new_time = ratio * duration

        self.seek_requested.emit(
            new_time
        )

    def update_timeline_width(self):

        duration = self.get_duration()

        if duration <= 0:
            return

        width = int(
            duration * self.zoom
        )

        self.setMinimumWidth(width)

        self.update()

    def set_duration(
        self,
        duration
    ):

        self.duration = duration

        self.update()

    def wheelEvent(self, event):

        delta = event.angleDelta().y()

        if delta > 0:

            self.set_zoom(
                self.zoom * 1.1
            )

        else:

            self.set_zoom(
                self.zoom / 1.1
            )

    def compute_fit_zoom(self):

        duration = self.get_duration()

        if duration <= 0:
            return 1.0

        parent_width = max(
            self.parent().width()
            if self.parent()
            else 1000,
            1000
        )

        return parent_width / duration

    def get_time_step(self):

        duration = self.get_duration()

        if duration <= 0:
            return 60

        pixels_per_second = (
            self.width() / duration
        )

        candidate_steps = [
            1,
            5,
            10,
            30,
            60,
            300,
            600,
            900,
            1800,
            3600
        ]

        for step in candidate_steps:

            pixels = (
                step * pixels_per_second
            )

            if pixels >= 80:
                return step

        return candidate_steps[-1]

    def contextMenuEvent(self, event):

        click_pos = event.pos()

        selected_block = None

        for rect, block in self.block_rects:

            if rect.contains(
                click_pos.x(),
                click_pos.y()
            ):

                selected_block = block
                break

        if selected_block is None:
            return

        menu = QMenu(self)

        actions = {}

        for speaker in self.project.speakers:

            action = menu.addAction(
                speaker.name
            )

            actions[action] = speaker.id

        menu.addSeparator()

        new_speaker_action = menu.addAction(
            "+ Nouvel intervenant..."
        )
        selected_action = menu.exec(
            event.globalPos()
        )

        if not selected_action:
            return

        elif selected_action == new_speaker_action:
            self.new_speaker_requested.emit()
            return

        else :
            speaker_id = selected_action.data()
        # if selected_action:

        #     speaker_id = actions[
        #         selected_action
        #     ]

            self.speaker_change_requested.emit(
                selected_block.id,
                speaker_id
            )

    def ensure_time_visible(
        self,
        time_position
    ):

        scroll = self.parent()

        while scroll and not hasattr(
            scroll,
            "horizontalScrollBar"
        ):
            scroll = scroll.parent()

        if not scroll:
            return

        duration = self.get_duration()

        if duration <= 0:
            return

        x = (
            time_position
            / duration
        ) * self.width()

        viewport_width = (
            scroll.viewport().width()
        )

        scroll.horizontalScrollBar().setValue(
            int(
                x - viewport_width / 2
            )
        )  

    def mouseMoveEvent(self, event):

        if not self.dragging_cursor:
            return

        duration = self.get_duration()

        ratio = (
            event.position().x()
            / self.width()
        )

        ratio = max(
            0.0,
            min(ratio, 1.0)
        )

        new_time = (
            ratio * duration
        )

        self.current_time = new_time

        self.seek_requested.emit(
            new_time
        )

        self.update()
    
    def mouseReleaseEvent(self, event):

        self.dragging_cursor = False

    def is_current_time_visible(self):

        scroll = self.parent()

        while scroll and not hasattr(
            scroll,
            "horizontalScrollBar"
        ):
            scroll = scroll.parent()

        if not scroll:
            return True

        duration = self.get_duration()

        if duration <= 0:
            return True

        cursor_x = (
            self.current_time
            / duration
        ) * self.width()

        scroll_x = (
            scroll.horizontalScrollBar()
            .value()
        )

        viewport_width = (
            scroll.viewport().width()
        )

        return (
            scroll_x
            <= cursor_x
            <= scroll_x + viewport_width
        )

    def ensure_cursor_visible(self):

        if self.timeline_scroll is None:
            return

        duration = self.get_duration()

        if duration <= 0:
            return

        cursor_x = (
            self.current_time
            / duration
        ) * self.width()

        scrollbar = (
            self.timeline_scroll.horizontalScrollBar()
        )

        left = scrollbar.value()

        viewport_width = (
            self.timeline_scroll.viewport().width()
        )

        right = left + viewport_width

        if cursor_x < left or cursor_x > right:

            scrollbar.setValue(
                int(
                    cursor_x
                    - viewport_width / 2
                )
            )