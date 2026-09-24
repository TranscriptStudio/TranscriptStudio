# ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QMessageBox,
    QFileDialog,
    QSplitter,
    QSizePolicy,
    QInputDialog,
)

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence
from pathlib import Path


from ui.block_widget import BlockWidget
from ui.edit_word_dialog import (EditWordDialog)
from ui.export_dialog import (ExportDialog)
from ui.timeline_widget import TimelineWidget
from ui.timeline_speaker_panel import TimelineSpeakerPanel

from services.playback import PlaybackManager
from services.project_io import (save_project)
from services.exporter import (TranscriptExporter)
from services.help import open_user_manual


class MainWindow(QMainWindow):

    def __init__(self, project):
        super().__init__()

        self.menuBar().hide()
        self.project = project

        self.playback = PlaybackManager()

        self.current_duration = 0
        
        self.block_widgets = {}

        self.current_block_id = None

        self.timeline_scroll = None

        self.setWindowTitle("ElevenLabs Transcript Editor")

        self.resize(1200,800)

        self.build_ui()

        self.update_window_title()
        self.setWindowState(
            self.windowState()
            | Qt.WindowState.WindowMaximized
        )

        self.save_shortcut = QShortcut(
            QKeySequence("Ctrl+S"),
            self
        )

        if self.project.audio_file:
            # print(
            #     f"Chargement audio : "
            #     f"{self.project.audio_file}"
            # )

            self.playback.load_file(
                self.project.audio_file
            )


        self.current_word_index = None
        self.autosave_timer = QTimer()

        self.autosave_timer.start(
            30000
        )
        self.connect_signals()

        self.zoom_plus_button.clicked.connect(
            self.timeline.zoom_in
        )

        self.zoom_minus_button.clicked.connect(
            self.timeline.zoom_out
        )
  
    def build_ui(self):

        main_widget = QWidget()
        root_layout = QVBoxLayout(main_widget)
        
        action_layout = QHBoxLayout()
        # Barre d'icones
        self.home_button = QPushButton("🏠")
        self.save_button = QPushButton("💾")
        self.export_button = QPushButton("📤")
        self.help_button = QPushButton("📖")

        
        self.home_button.setToolTip(
            "Retour à l'accueil"
        )

        self.save_button.setToolTip(
            "Enregistrer le projet"
        )

        self.export_button.setToolTip(
            "Exporter la transcription"
        )
        self.help_button.setToolTip(
            "Ouvrir le manuel utilisateur"
        )
        action_layout.addWidget(
            self.home_button
        )

        action_layout.addWidget(
            self.save_button
        )

        action_layout.addWidget(
            self.export_button
        )
        action_layout.addWidget(
            self.help_button
        )
        action_layout.addSpacing(50)

        self.zoom_label = QLabel("Zoom timeline :")
        self.zoom_fit_button = QPushButton("⛶")
        self.zoom_minus_button = QPushButton("-")
        self.zoom_plus_button = QPushButton("+")
        
        self.zoom_minus_button.setToolTip(
            "réduire le zoom sur la timeline"
        )
        self.zoom_plus_button.setToolTip(
            "Augmenter le zoom sur la timeline"
        )
        self.zoom_fit_button.setToolTip(
            "ajuster à à la durée totale"
        )
        action_layout.addWidget(self.zoom_label)
        action_layout.addWidget(self.zoom_fit_button)
        action_layout.addWidget(
            self.zoom_minus_button
        )

        action_layout.addWidget(
            self.zoom_plus_button
        )
        self.cleanup_speakers_button = QPushButton("🧹")
        self.cleanup_speakers_button.setToolTip(
            "Supprimer les intervenants non utilisés"
        )
        action_layout.addWidget(
            self.cleanup_speakers_button
        )

        # action_layout.addStretch()

        action_layout.addSpacing(50)

        #
        # Lecteur audio
        #
        self.btn_prev = QPushButton("⏪")
        self.btn_play = QPushButton("▶")
        self.btn_next = QPushButton("⏩")

        self.time_label = QLabel("00:00 / 00:00")
        self.btn_prev.setToolTip("Reculer l'audio de 5s")
        self.btn_next.setToolTip("Avance l'audio de 5s")
        self.btn_play.setToolTip("Lecture audio")
        self.btn_prev.setFixedSize(40, 30)
        self.btn_play.setFixedSize(50, 30)
        self.btn_next.setFixedSize(40, 30)

        action_layout.addWidget(
            self.btn_prev
        )

        action_layout.addWidget(
            self.btn_play
        )

        action_layout.addWidget(
            self.btn_next
        )

        action_layout.addWidget(
            self.time_label
        )
        
        action_layout.addStretch()
        root_layout.addLayout(action_layout)
        for btn in [
            self.home_button,
            self.save_button,
            self.export_button,
            self.btn_prev,
            self.btn_play,
            self.btn_next,
        ]:
            btn.setFixedSize(36, 36)
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #E8E8E8;
                    border-radius: 4px;
                }
                """)


        #
        # Zone scrollable contenant les blocs
        #
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        container = QWidget()

        self.main_layout = QVBoxLayout(container)
        self.main_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        self.main_layout.setSpacing(2)

        self.scroll.setWidget(container)

        #
        # Splitter vertical
        #
        splitter = QSplitter(
            Qt.Orientation.Vertical
        )

        splitter.addWidget(
            self.scroll
        )

        #
        # Timeline
        #
        timeline_container = QWidget()

        timeline_layout = QHBoxLayout(
            timeline_container
        )

        timeline_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        timeline_layout.setSpacing(0)

        #
        # Speakers
        #
        self.timeline_speakers = TimelineSpeakerPanel(
            self.project
        )

        #
        # Timeline
        #
        self.timeline = TimelineWidget(
            self.project
        )

        self.timeline_scroll = QScrollArea()

        self.timeline.timeline_scroll = (
            self.timeline_scroll
        )
        #
        # Assemblage
        #
        timeline_layout.addWidget(
            self.timeline_speakers
        )

        timeline_layout.addWidget(
            self.timeline,
            1
        )

        #
        # ScrollArea unique pour la timeline
        #
        

        self.timeline_scroll.setWidget(
            timeline_container
        )

        self.timeline_scroll.setWidgetResizable(
            True
        )

        splitter.addWidget(
            self.timeline_scroll
        )

        splitter.setSizes([
            700,
            200
        ])

        root_layout.addWidget(
            splitter
        )

        self.setCentralWidget(
            main_widget
        )
        QTimer.singleShot(
            0,
            self.timeline.zoom_fit
        )
        self.populate_blocks()

    def populate_blocks(self):

        speaker_names = [
            speaker.name
            for speaker in self.project.speakers
        ]

        for i, block in enumerate(self.project.blocks):
            speaker = (self.project.get_speaker_by_id(block.speaker_id))
            text = (self.project.get_block_text(block))
            widget = BlockWidget(
                project=self.project,
                block=block,
                speaker_names=speaker_names,
                current_speaker_name=speaker.name,
                )
            widget.word_clicked.connect(self.on_word_clicked)
            self.block_widgets[block.id] = widget
            self.main_layout.addWidget(widget)
            
            #
            # Fusion possible ?
            #
            if i < len(self.project.blocks) - 1:

                next_block = self.project.blocks[i + 1]

                if block.speaker_id == next_block.speaker_id:

                    merge_button = QPushButton("⛓")

                    merge_button.setStyleSheet("""
                        QPushButton {
                            border: none;
                            background: transparent;
                            font-size: 14px;
                        }

                        QPushButton:hover {
                            color: #4A90E2;
                        }
                    """)

                    merge_button.setFixedWidth(40)

                    merge_button.clicked.connect(
                        lambda checked=False,
                        b1=block.id,
                        b2=next_block.id:
                        self.merge_blocks(
                            b1,
                            b2
                        )
                    )

                    self.main_layout.addWidget(
                        merge_button
                    )
            widget.speaker_changed.connect(self.on_speaker_changed)
            widget.rename_speaker_requested.connect(self.rename_speaker)
            widget.edit_word_requested.connect(self.edit_word)
            widget.split_before_requested.connect(self.split_block_before)
            widget.split_after_requested.connect(self.split_block_after)
            widget.new_speaker_requested.connect(self.create_new_speaker)


        self.main_layout.addStretch()
  
    def connect_signals(self):
        

        self.btn_play.clicked.connect(
            self.playback.toggle_play_pause
        )

        self.btn_prev.clicked.connect(
            lambda: self.playback.jump_backward(5)
        )

        self.btn_next.clicked.connect(
            lambda: self.playback.jump_forward(5)
        )
        self.playback.position_changed.connect(
            self.update_position
        )
        self.playback.position_changed.connect(
            self.update_active_block
        )
        self.playback.duration_changed.connect(
            self.timeline.set_duration
        )
        self.playback.position_changed.connect(
            self.timeline.set_current_time
        )

        self.timeline.seek_requested.connect(
            self.on_timeline_seek
        )
        self.home_button.clicked.connect(
            self.return_to_home
        )

        self.save_button.clicked.connect(
            self.save_current_project
        )

        self.export_button.clicked.connect(
            self.export_project
        )
        self.save_shortcut.activated.connect(
            self.save_current_project
        )
        self.playback.playing_changed.connect(
            self.update_play_button
        )
        self.autosave_timer.timeout.connect(
            self.autosave_project
        )
        self.zoom_fit_button.clicked.connect(
            self.timeline.zoom_fit
        )
        self.timeline.speaker_change_requested.connect(
            self.timeline_change_speaker
        )
        self.timeline_speakers.rename_speaker_requested.connect(
            self.timeline_rename_speaker
        )
        self.help_button.clicked.connect(
            open_user_manual
        )
        self.timeline.new_speaker_requested.connect(
            self.create_new_speaker
        )
        self.cleanup_speakers_button.clicked.connect(
            self.cleanup_unused_speakers
        )
        
    def format_time(self, seconds):

        minutes = int(seconds // 60)
        seconds = int(seconds % 60)

        return f"{minutes:02}:{seconds:02}"

    def update_duration(self, duration):

        self.current_duration = duration

        self.time_label.setText(
            f"{self.format_time(0)} / "
            f"{self.format_time(duration)}"
        )

    def update_position(self, position):

        self.time_label.setText(
            f"{self.format_time(position)} / "
            f"{self.format_time(self.current_duration)}"
        )

    def update_play_button(self, playing):

        if playing:
            self.btn_play.setText("⏸")
        else:
            self.btn_play.setText("▶")

    def update_active_block(
        self,
        current_time
    ):
        word_index = (
            self.project.find_word_at_time(
                current_time
            )
        )

        if word_index is None:
            return

        block = (
            self.project
            .get_block_for_word(
                word_index
            )
        )

        if block is None:
            return

        widget = self.block_widgets.get(
            block.id
        )

        #
        # Le modèle et l'interface peuvent être
        # brièvement désynchronisés pendant une
        # reconstruction des blocs.
        #
        if widget is None:
            return

        #
        # Mise à jour du mot actif uniquement
        # lorsque le mot change.
        #
        if (
            word_index
            != self.current_word_index
        ):
            self.current_word_index = (
                word_index
            )

            for block_widget in (
                self.block_widgets.values()
            ):
                block_widget.set_active_word(
                    None
                )

            widget.set_active_word(
                word_index
            )

        #
        # Pas de changement de bloc.
        #
        if (
            block.id
            == self.current_block_id
        ):
            return

        #
        # Désactiver l'ancien bloc uniquement
        # s'il existe encore dans l'interface.
        #
        if self.current_block_id is not None:
            old_widget = (
                self.block_widgets.get(
                    self.current_block_id
                )
            )

            if old_widget is not None:
                old_widget.set_active(
                    False
                )

        #
        # Le nouveau bloc devient le bloc actif.
        #
        self.current_block_id = (
            block.id
        )

        widget.set_active(
            True
        )
        
    def on_word_clicked(self, word_index):

        word = self.project.words[word_index]

        self.playback.set_position(
            word.start
        )

    def scroll_to_widget(self, widget):

        scroll_bar = self.scroll.verticalScrollBar()

        viewport_height = (
            self.scroll.viewport().height()
        )

        widget_top = widget.pos().y()

        widget_bottom = (
            widget_top + widget.height()
        )

        visible_top = scroll_bar.value()

        visible_bottom = (
            visible_top + viewport_height
        )

        #
        # widget au-dessus
        #
        if widget_top < visible_top:

            scroll_bar.setValue(
                widget_top - 20
            )

        #
        # widget en dessous
        #
        elif widget_bottom > visible_bottom:

            scroll_bar.setValue(
                widget_bottom
                - viewport_height
                + 20
            )

    def is_widget_fully_visible(self, widget):

        widget_top = widget.pos().y()

        widget_bottom = (
            widget_top + widget.height()
        )

        visible_top = (
            self.scroll.verticalScrollBar().value()
        )

        visible_bottom = (
            visible_top
            + self.scroll.viewport().height()
        )

        return (
            widget_top >= visible_top
            and widget_bottom <= visible_bottom
        )

    def on_speaker_changed(
        self,
        block_id,
        speaker_id
    ):

        block = self.project.get_block_by_id(
            block_id
        )

        if block is None:
            return

        block.speaker_id = speaker_id

        self.project.mark_modified()

        self.update_window_title()
        
        self.reload_blocks()

    def rename_speaker(
        self,
        speaker_id,
        new_name
    ):

        new_name = new_name.strip()

        if not new_name:
            return

        speaker = self.project.get_speaker_by_id(
            speaker_id
        )

        if speaker is None:
            return

        speaker.name = new_name

        self.refresh_speaker_names()
        self.timeline_speakers.update()
        self.timeline.update()  
        self.project.mark_modified()

        self.update_window_title()

    def refresh_speaker_names(self):
        speaker_names = (self.project.get_speaker_names())
        for widget in self.block_widgets.values():
            speaker = self.project.get_speaker_by_id(widget.block.speaker_id)
            # Nom affiché
            widget.speaker_name_edit.setText(speaker.name)
            # Combo caché
            widget.speaker_combo.blockSignals(True)

            widget.speaker_combo.clear()

            widget.speaker_combo.addItems(speaker_names)

            widget.speaker_combo.setCurrentText(speaker.name)

            widget.speaker_combo.blockSignals(False)

    def split_block_before(
        self,
        block_id,
        word_index
    ):

        self.project.split_block(
            block_id,
            word_index
        )
        self.project.mark_modified()

        self.update_window_title()
        self.reload_blocks()

    def split_block_after(
        self,
        block_id,
        word_index
    ):

        self.project.split_block_after(
            block_id,
            word_index
        )
        self.project.mark_modified()

        self.update_window_title()
        self.reload_blocks()

    def reload_blocks(self):
        #
        # Supprimer les widgets existants.
        #
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        #
        # Réinitialiser complètement l'état
        # associé aux anciens widgets.
        #
        self.block_widgets.clear()

        self.current_block_id = None
        self.current_word_index = None

        #
        # Recréer les blocs.
        #
        self.populate_blocks()

    def merge_blocks(
        self,
        first_block_id,
        second_block_id
    ):

        result = self.project.merge_blocks(
            first_block_id,
            second_block_id
        )

        if result:
            self.project.mark_modified()

            self.update_window_title()

            self.reload_blocks()

    def edit_word(
        self,
        word_index
    ):

        word = self.project.words[
            word_index
        ]

        dialog = EditWordDialog(
            word.text,
            self
        )

        result = dialog.exec()

        if not result:
            return

        if dialog.delete_requested:

            self.project.delete_word(
                word_index
            )

        else:

            self.project.replace_word_text(
                word_index,
                dialog.get_text()
            )
        self.project.mark_modified()

        self.update_window_title()

        self.reload_blocks()

    def update_window_title(self):

        title = (
            "Transcript Editor for ElevenLabs"
        )

        if self.project.project_file:

            title += (
                " | "
                + Path(
                    self.project.project_file
                ).parent.name
            )

        else:

            title += (
                " | "
                + self.project.name
            )

        if self.project.modified:

            title += " *"

        self.setWindowTitle(title)

    def save_current_project(self):

        
        if not self.project.project_file:
            return

        save_project(
            self.project,
            self.project.project_file
        )

        self.project.mark_saved()

        self.update_window_title()
        
    def closeEvent(self, event):

        if not self.project.modified:

            event.accept()
            return

        reply = QMessageBox.question(
            self,
            "Projet modifié",
            "Le projet a été modifié.\n\n"
            "Voulez-vous enregistrer les modifications ?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Save:

            self.save_current_project()

            event.accept()

        elif reply == QMessageBox.StandardButton.Discard:

            event.accept()

        else:

            event.ignore()

    def autosave_project(self):

        if not self.project.modified:
            return

        self.save_current_project()

    def export_project(self):

        dialog = ExportDialog(
            self.project,
            self
        )

        if not dialog.exec():
            return

        options = dialog.get_options()

        exporter = TranscriptExporter()

        extension = options["format"]

        default_name = Path(
                        self.project.name
                    ).stem
        filters = (
            "Texte (*.txt);;"
            "JSON (*.json);;"
            "Word (*.docx);;"
            "PDF (*.pdf)"
        )

        selected_filter = {
            "txt": "Texte (*.txt)",
            "json": "JSON (*.json)",
            "docx": "Word (*.docx)",
            "pdf": "PDF (*.pdf)"
        }[extension]

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter la transcription",
            f"{default_name}.{extension}",
            filters,
            selected_filter
        )
        

        if not filename:
            return

        if options["format"] == "txt":

            exporter.export_txt(
                self.project,
                filename,
                options["include_speakers"],
                options["include_timestamps"]
            )

        elif options["format"] == "json":

            exporter.export_json(
                self.project,
                filename,
                options["include_speakers"],
                options["include_timestamps"]
            )

        elif options["format"] == "docx":

            exporter.export_docx(
                self.project,
                filename,
                options["include_speakers"],
                options["include_timestamps"]
            )

        elif options["format"] == "pdf":

            exporter.export_pdf(
                self.project,
                filename,
                options["include_speakers"],
                options["include_timestamps"]
            )

    def return_to_home(self):

        if self.project.modified:

            self.save_current_project()

        from ui.home_window import HomeWindow

        self.home_window = HomeWindow()

        self.home_window.show()

        self.close()

    def on_timeline_seek(
        self,
        position
    ):

        self.playback.set_position(position)

        word_index = self.project.find_word_at_time(
            position
        )

        if word_index is None:
            return

        block = self.project.get_block_for_word(
            word_index
        )

        if block is None:
            return

        widget = self.block_widgets.get(
            block.id
        )

        if widget is not None:

            self.scroll.ensureWidgetVisible(
                widget,
                20,
                100
            )

    def timeline_change_speaker(
        self,
        block_id,
        speaker_id
    ):

        block = self.project.get_block_by_id(
            block_id
        )

        if block is None:
            return

        block.speaker_id = speaker_id

        self.project.mark_modified()

        self.reload_blocks()

        self.timeline.update()

        self.update_window_title()

    def timeline_rename_speaker(
        self,
        speaker_id,
        current_name
    ):
        new_name, ok = QInputDialog.getText(
            self,
            "Renommer l'intervenant",
            "Nom :",
            text=current_name
        )
        speaker = self.project.get_speaker_by_id(
            speaker_id
        )

        speaker.name = new_name
        self.refresh_speaker_names()

        self.timeline_speakers.update()

        self.timeline.update()

    def create_new_speaker(self,block_id):

        name, ok = QInputDialog.getText(
            self,
            "Nouvel intervenant",
            "Nom :"
        )

        if not ok:
            return

        name = name.strip()

        if not name:
            return

        existing_ids = [
            s.id
            for s in self.project.speakers
        ]

        next_id = (
            f"speaker_{len(existing_ids)}"
        )

        from models.speaker import Speaker
        from services.elevenlabs_importer import DEFAULT_COLORS
        color = DEFAULT_COLORS[
                    len(self.project.speakers)
                    % len(DEFAULT_COLORS)
                ]
        speaker = Speaker(
            id=next_id,
            name=name,
            color=color
        )

        self.project.speakers.append(
            speaker
        )
        block = self.project.get_block_by_id(
            block_id
        )

        if block is not None:

            block.speaker_id = speaker.id

        self.project.mark_modified()
        self.refresh_speaker_names()
        self.reload_blocks()

        self.timeline_speakers.update()

        self.timeline.update()

    def cleanup_unused_speakers(self):

        used_speaker_ids = {
            block.speaker_id
            for block in self.project.blocks
        }

        before = len(
            self.project.speakers
        )

        self.project.speakers = [

            speaker

            for speaker in self.project.speakers

            if speaker.id in used_speaker_ids

        ]

        removed = (
            before
            - len(self.project.speakers)
        )

        if removed:

            self.project.mark_modified()

            self.reload_blocks()

            self.timeline.update()

            self.timeline_speakers.update()

            self.update_window_title()

            QMessageBox.information(
                self,
                "Nettoyage",
                f"{removed} intervenant(s) supprimé(s)."
            )

        else:

            QMessageBox.information(
                self,
                "Nettoyage",
                "Aucun intervenant inutilisé."
            )
    

   