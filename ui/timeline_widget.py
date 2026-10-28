from PySide6.QtWidgets import (
    QWidget,
    QMenu,
    QScrollArea,
)

from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPalette,
)

from PySide6.QtCore import Qt, QRectF, Signal
ROW_HEIGHT = 23

HEADER_HEIGHT = 25

class TimelineWidget(QWidget):

    seek_requested = Signal(float)

    block_clicked = Signal(int)
    new_speaker_requested = Signal(int)
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



        self.header_height = 25
        self.zoom = 1.0
        self.fit_zoom = None
        self.min_zoom = 0.01
        self.max_zoom = 20.0
        self.base_pixels_per_second = 1.0
        self.zoom_fit()
        self.block_rects = []
        self.timeline_scroll = None
        #
        # Etats des interactions souris.
        #
        self.dragging_cursor = False
        self.panning = False
        self.mouse_pressed = False
        self.mouse_has_moved = False

        self.mouse_press_x = 0.0
        self.last_mouse_x = 0.0

        self.drag_threshold = 4
        self.setMouseTracking(
            True
        )

        #
        # Rectangle de la bulle du curseur.
        # Il sera recalculé dans paintEvent().
        #
        self.cursor_rect = QRectF()
        
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

    def apply_zoom_at_cursor(
        self,
        new_zoom
    ):
        duration = self.get_duration()

        if (
            duration <= 0
            or self.timeline_scroll is None
        ):
            return

        fit_zoom = (
            self.get_fit_zoom()
        )

        new_zoom = max(
            fit_zoom,
            min(
                new_zoom,
                self.max_zoom
            )
        )

        #
        # Rien à faire si le zoom
        # ne change réellement pas.
        #
        if abs(
            new_zoom - self.zoom
        ) < 0.000001:
            return

        self.zoom = new_zoom

        new_width = max(
            1,
            int(
                duration
                * self.zoom
            )
        )

        self.setFixedWidth(
            new_width
        )

        scrollbar = (
            self.timeline_scroll
            .horizontalScrollBar()
        )

        viewport_width = (
            self.timeline_scroll
            .viewport()
            .width()
        )

        cursor_x = (
            self.current_time
            / duration
            * new_width
        )

        #
        # Les boutons +/- sont explicitement
        # centrés sur le curseur de lecture.
        #
        scrollbar.setValue(
            int(
                cursor_x
                - viewport_width / 2
            )
        )

        self.update()
        
    def zoom_in(self):
        self.apply_zoom_at_cursor(
            self.zoom * 1.5
        )

    def zoom_out(self):
        self.apply_zoom_at_cursor(
            self.zoom / 1.5
        )

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
        palette = self.palette()

        text_color = palette.color(
            QPalette.ColorRole.Text
        )

        grid_color = palette.color(
            QPalette.ColorRole.Mid
        )

        bubble_color = palette.color(
            QPalette.ColorRole.Text
        )

        bubble_text_color = palette.color(
            QPalette.ColorRole.Base
        )

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        duration = self.get_duration()

        timeline_width = self.width()

        #
        # Correspondance speaker -> ligne
        #
        speaker_rows = {}

        self.header_height = HEADER_HEIGHT

        block_height =  self.row_height - 8
        #
        # Axe temporel
        #
        painter.setPen(
            text_color
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
            grid_color
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
            grid_color
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
            bubble_color
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
            bubble_text_color
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
 
    def mousePressEvent(
        self,
        event
    ):
        if (
            event.button()
            != Qt.MouseButton.LeftButton
        ):
            super().mousePressEvent(
                event
            )
            return

        click_pos = event.position()

        hit_rect = self.cursor_rect.adjusted(
            -8,
            -8,
            8,
            8
        )

        self.mouse_pressed = True
        self.mouse_has_moved = False
        self.panning = False

        self.mouse_press_x = (
            click_pos.x()
        )

        self.last_mouse_x = (
            click_pos.x()
        )

        #
        # La bulle du curseur a été attrapée.
        #
        if hit_rect.contains(
            click_pos
        ):
            self.dragging_cursor = True

            self.setCursor(
                Qt.CursorShape.ClosedHandCursor
            )

            event.accept()
            return

        #
        # Sinon il s'agit potentiellement
        # d'un clic simple ou d'un pan.
        #
        self.dragging_cursor = False

        event.accept()

    def _largeur_viewport(self) -> int:
        """
        Largeur du viewport du QScrollArea ancêtre
        (0 si la timeline n'est pas dans une zone
        défilable).
        """

        widget = self.parentWidget()

        while widget is not None:

            if isinstance(widget, QScrollArea):
                return widget.viewport().width()

            widget = widget.parentWidget()

        return 0

    def update_timeline_width(self):

        duration = self.get_duration()

        if duration <= 0:
            return

        width = int(
            duration * self.zoom
        )

        #
        # P16-bis (spec correctifs §10.2) : les pistes
        # s'étendent jusqu'au bord droit — dézoomé, la
        # timeline ne laisse jamais de marge vide à
        # droite du viewport.
        #
        viewport = self._largeur_viewport()

        if viewport > 0:
            width = max(width, viewport)

        self.setFixedWidth(width)

        self.update()

    def set_duration(
        self,
        duration
    ):

        self.duration = duration

        self.update()

    def update_mouse_cursor(
        self,
        position
    ):
        if self.dragging_cursor:
            self.setCursor(
                Qt.CursorShape.ClosedHandCursor
            )
            return

        hit_rect = self.cursor_rect.adjusted(
            -8,
            -8,
            8,
            8
        )

        if hit_rect.contains(position):
            self.setCursor(
                Qt.CursorShape.OpenHandCursor
            )
        else:
            self.setCursor(
                Qt.CursorShape.ArrowCursor
            )

    def wheelEvent(
        self,
        event
    ):
        if self.timeline_scroll is None:
            event.ignore()
            return

        duration = self.get_duration()

        if duration <= 0:
            event.ignore()
            return

        old_width = self.width()

        if old_width <= 0:
            event.ignore()
            return

        scrollbar = (
            self.timeline_scroll
            .horizontalScrollBar()
        )

        #
        # event.position().x() est une coordonnée
        # locale dans TimelineWidget.
        #
        mouse_widget_x = (
            event.position().x()
        )

        #
        # Position de la souris dans le viewport.
        #
        mouse_viewport_x = (
            mouse_widget_x
            - scrollbar.value()
        )

        #
        # Temps actuellement situé sous la souris.
        #
        time_under_mouse = (
            mouse_widget_x
            / old_width
            * duration
        )

        delta = (
            event.angleDelta().y()
        )

        if delta > 0:
            new_zoom = (
                self.zoom * 1.1
            )
        elif delta < 0:
            new_zoom = (
                self.zoom / 1.1
            )
        else:
            return

        fit_zoom = self.get_fit_zoom()

        self.zoom = max(
            fit_zoom,
            min(
                new_zoom,
                self.max_zoom
            )
        )

        #
        # Calcul direct de la nouvelle largeur.
        #
        new_width = max(
            1,
            int(
                duration
                * self.zoom
            )
        )

        if new_width != self.width():
            self.setFixedWidth(
                new_width
            )

        #
        # Nouvelle position X du même instant.
        #
        new_time_x = (
            time_under_mouse
            / duration
            * new_width
        )

        #
        # Repositionner le scroll pour conserver
        # ce temps sous la souris.
        #
        new_scroll = (
            new_time_x
            - mouse_viewport_x
        )

        scrollbar.setValue(
            int(new_scroll)
        )

        self.update()

        event.accept()

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

    def contextMenuEvent(
        self,
        event
    ):
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

            actions[action] = (
                speaker.id
            )

        menu.addSeparator()

        new_speaker_action = menu.addAction(
            "+ Nouvel intervenant..."
        )

        selected_action = menu.exec(
            event.globalPos()
        )

        #
        # Menu fermé sans sélection.
        #
        if selected_action is None:
            return

        #
        # Création d'un nouvel intervenant.
        #
        if selected_action == new_speaker_action:
            self.new_speaker_requested.emit(
                selected_block.id
            )
            return

        #
        # Récupérer l'ID réellement associé
        # à l'action sélectionnée.
        #
        speaker_id = actions.get(
            selected_action
        )

        if not speaker_id:
            return

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

    def mouseMoveEvent(
        self,
        event
    ):
        position = event.position()

        #
        # Aucun bouton enfoncé :
        # uniquement mise à jour du pointeur.
        #
        if not self.mouse_pressed:
            self.update_mouse_cursor(
                position
            )
            return

        current_x = (
            position.x()
        )

        total_movement = (
            current_x
            - self.mouse_press_x
        )

        if (
            not self.mouse_has_moved
            and abs(total_movement)
            >= self.drag_threshold
        ):
            self.mouse_has_moved = True

        #
        # CAS 1
        # Drag du curseur.
        #
        if self.dragging_cursor:
            duration = self.get_duration()

            if duration <= 0:
                return

            ratio = (
                current_x
                / self.width()
            )

            ratio = max(
                0.0,
                min(
                    ratio,
                    1.0
                )
            )

            new_time = (
                ratio
                * duration
            )

            self.current_time = (
                new_time
            )

            self.seek_requested.emit(
                new_time
            )

            self.setCursor(
                Qt.CursorShape.ClosedHandCursor
            )

            self.update()
            event.accept()
            return

        #
        # Pas encore assez de mouvement :
        # cela peut toujours être un clic simple.
        #
        if not self.mouse_has_moved:
            return

        #
        # CAS 2
        # Pan de la timeline.
        #
        fit_zoom = (
            self.get_fit_zoom()
        )

        if self.zoom <= fit_zoom:
            return

        if self.timeline_scroll is None:
            return

        self.panning = True

        dx = (
            current_x
            - self.last_mouse_x
        )

        self.last_mouse_x = (
            current_x
        )

        scrollbar = (
            self.timeline_scroll
            .horizontalScrollBar()
        )

        scrollbar.setValue(
            scrollbar.value()
            - int(dx)
        )

        event.accept()
    
    def mouseReleaseEvent(
        self,
        event
    ):
        if (
            event.button()
            != Qt.MouseButton.LeftButton
        ):
            super().mouseReleaseEvent(
                event
            )
            return

        release_pos = (
            event.position()
        )

        was_dragging_cursor = (
            self.dragging_cursor
        )

        was_panning = (
            self.panning
        )

        was_moved = (
            self.mouse_has_moved
        )

        #
        # Réinitialiser les états.
        #
        self.mouse_pressed = False
        self.dragging_cursor = False
        self.panning = False
        self.mouse_has_moved = False

        #
        # Remettre le pointeur adapté
        # à la position actuelle.
        #
        self.update_mouse_cursor(
            release_pos
        )

        #
        # Un drag curseur est terminé.
        #
        if was_dragging_cursor:
            event.accept()
            return

        #
        # Un pan est terminé.
        #
        if was_panning or was_moved:
            event.accept()
            return

        #
        # CAS 3
        # Clic simple :
        # positionner le curseur.
        #
        duration = self.get_duration()

        if duration <= 0:
            return

        ratio = (
            release_pos.x()
            / self.width()
        )

        ratio = max(
            0.0,
            min(
                ratio,
                1.0
            )
        )

        new_time = (
            ratio
            * duration
        )

        self.seek_requested.emit(
            new_time
        )

        event.accept()

    def leaveEvent(
        self,
        event
    ):
        if not self.dragging_cursor:
            self.setCursor(
                Qt.CursorShape.ArrowCursor
            )

        super().leaveEvent(
            event
        )

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