# ui/audio_preprocess_dialog.py

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QSizePolicy,
    QSlider,
    QCheckBox,
    QSplitter,
    QLineEdit,
)
from PySide6.QtMultimedia import (
    QMediaPlayer,
    QAudioOutput
)

from PySide6.QtCore import Qt, QUrl
from pathlib import Path

from models.audio_processing_settings import AudioProcessingSettings
from services.playback import PlaybackManager
from services.audio_waveform_service import AudioWaveformService
from services.audio_processing_pipeline import  AudioProcessingPipeline


from ui.waveform_widget import WaveformWidget

class AudioPreprocessDialog(QDialog):

    def __init__(
        self,
        audio_file,
        parent=None
    ):

        super().__init__(parent)
        self.trim_start_enabled = False
        self.trim_end_enabled = False

        self.trim_start_time = 0.0
        self.trim_end_time = 0.0
        self.setWindowFlag(
            Qt.WindowMinMaxButtonsHint,
            True
        )
        self.setWindowModality(
            Qt.WindowModal
        )
        self.audio_file = audio_file


        self.settings = (
            AudioProcessingSettings()
        )

        self.playback = PlaybackManager()

        self.playback.load_file(self.audio_file)

        self.setWindowTitle("Prétraitement audio")

        self.resize(1200, 700)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        self.setWindowTitle(
            f"Prétraitement audio - {Path(self.audio_file).name}"
        )

        #
        # Future waveform
        #
        self.waveform_widget = (
            WaveformWidget()
        )
        self.waveform_widget.load_audio(
            self.audio_file
        )
        self.working_wav = (
            self.waveform_widget.document.working_wav
        )

        self.waveform_widget.setMinimumHeight(
            80
        )

        toolbar = QHBoxLayout()

        self.play_button = QPushButton("▶")

        self.pause_button = QPushButton("⏸")

        self.stop_button = QPushButton("⏹")

        self.zoom_in_button = QPushButton("➕")

        self.zoom_out_button = QPushButton("➖")

        self.fit_button = QPushButton("↔️")

        self.process_button = QPushButton("✨ Lancer le traitement")

        self.restore_button = QPushButton("↶ Annuler les modifications")

        self.save_button = QPushButton("💾")

        self.transcribe_button = QPushButton("☁")

        for btn in [
            self.play_button,
            self.pause_button,
            self.stop_button,
            self.zoom_in_button,
            self.zoom_out_button,
            self.fit_button,
            self.process_button,
            self.restore_button,
            self.save_button,
            self.transcribe_button,
        ]:

            btn.setFixedSize(40, 40)
            if btn == self.process_button:
                btn.setFixedSize(150, 40)
            if btn == self.restore_button:
                btn.setFixedSize(190, 40)
            toolbar.addWidget(btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.position_slider = QSlider(
            Qt.Horizontal   
        )
        self.position_slider.setFixedHeight(20)
        # layout.addWidget(
        #     self.position_slider,
        #     stretch=0
        # )
        self.position_label = QLabel(
            "00:00 / 00:00"
        )

        self.position_label.setFixedWidth(90)

        position_layout = QHBoxLayout()

        position_layout.addWidget(
            self.position_slider
        )
        position_layout.addWidget(self.position_label)

        layout.addLayout(
            position_layout
        )

        self.effects_panel = QWidget()

        self.effects_panel.setMinimumHeight(
            140
        )
        effects_title = QLabel("Options de traitement")

        effects_title.setStyleSheet("""
            font-weight: bold;
            font-size: 12px;
        """)        
        effects_layout = QVBoxLayout(
            self.effects_panel
        )
        effects_layout.setAlignment(
            Qt.AlignTop
        )
        effects_layout.setContentsMargins(
            10,
            5,
            10,
            5
        )

        effects_layout.setSpacing(
            6
        )
        self.trim_checkbox = QCheckBox(
            "Découpe"
        )

        self.trim_start_edit = QLineEdit(
            "00:00:00.000"
        )

        self.trim_end_edit = QLineEdit(
            "00:00:00.000"
        )

        self.trim_duration_label = QLabel(
            "Durée conservée : 00:00:00.000"
        )

        self.trim_start_edit.setFixedWidth(
            110
        )

        self.trim_end_edit.setFixedWidth(
            110
        )

        self.trim_start_edit.setEnabled(
            False
        )

        self.trim_end_edit.setEnabled(
            False
        )

        

        self.silence_checkbox = QCheckBox(
            "Supprimer les silences"
        )
        self.silence_threshold_edit = QLineEdit(
            "-35"
        )

        self.silence_duration_edit = QLineEdit(
            "0.5"
        )

        self.silence_threshold_edit.setFixedWidth(
            80
        )

        self.silence_duration_edit.setFixedWidth(
            80
        )

        self.silence_threshold_edit.setEnabled(
            False
        )

        self.silence_duration_edit.setEnabled(
            False
        )
        self.speed_checkbox = QCheckBox(
            "Accélérer"
        )
        effects_layout.addWidget(
            effects_title
        )

        trim_layout = QVBoxLayout()

        trim_header_layout = QHBoxLayout()

        trim_header_layout.addWidget(
            self.trim_checkbox
        )

        trim_header_layout.addStretch()

        trim_layout.addLayout(
            trim_header_layout
        )

        trim_values_layout = QHBoxLayout()

        trim_values_layout.addWidget(
            QLabel("Début :")
        )

        trim_values_layout.addWidget(
            self.trim_start_edit
        )

        trim_values_layout.addSpacing(
            20
        )

        trim_values_layout.addWidget(
            QLabel("Fin :")
        )

        trim_values_layout.addWidget(
            self.trim_end_edit
        )

        trim_values_layout.addStretch()

        trim_layout.addLayout(
            trim_values_layout
        )

        trim_layout.addWidget(
            self.trim_duration_label
        )

        effects_layout.addLayout(
            trim_layout
        )

        silence_layout = QVBoxLayout()

        silence_layout.addWidget(
            self.silence_checkbox
        )

        threshold_layout = QHBoxLayout()

        threshold_layout.addWidget(
            QLabel("Seuil (dB) :")
        )

        threshold_layout.addWidget(
            self.silence_threshold_edit
        )

        threshold_layout.addStretch()

        silence_layout.addLayout(
            threshold_layout
        )

        duration_layout = QHBoxLayout()

        duration_layout.addWidget(
            QLabel("Durée mini (s) :")
        )

        duration_layout.addWidget(
            self.silence_duration_edit
        )

        duration_layout.addStretch()

        silence_layout.addLayout(
            duration_layout
        )

        effects_layout.addLayout(
            silence_layout
        )

        effects_layout.addWidget(
            self.speed_checkbox
        )
        effects_layout.addStretch()
        
        self.trim_checkbox.setChecked(
            self.settings.trim_start_enabled
        )

        self.trim_start_edit.setEnabled(
            self.settings.trim_start_enabled
        )

        self.trim_end_edit.setEnabled(
            self.settings.trim_start_enabled
        )
        self.silence_checkbox.setChecked(
            self.settings.silence_enabled
        )

        self.silence_threshold_edit.setEnabled(
            self.settings.silence_enabled
        )

        self.silence_duration_edit.setEnabled(
            self.settings.silence_enabled
        )        

        splitter = QSplitter(
            Qt.Vertical
        )
        splitter.setChildrenCollapsible(
            False
        )
        splitter.addWidget(
            self.waveform_widget
        )

        splitter.addWidget(
            self.effects_panel
        )

        splitter.setSizes([
            450,
            180,
        ])

        layout.addWidget(
            splitter,
            stretch=1
        )
        self.play_button.clicked.connect(
            self.playback.play
        )

        self.pause_button.clicked.connect(
            self.playback.pause
        )

        self.stop_button.clicked.connect(
            self.playback.stop
        )

        self.zoom_in_button.clicked.connect(
            self.waveform_widget.zoom_in
        )

        self.zoom_out_button.clicked.connect(
            self.waveform_widget.zoom_out
        )

        self.fit_button.clicked.connect(
            self.waveform_widget.fit_all
        )
        self.playback.position_changed.connect(
            self.update_position
        )

        self.playback.duration_changed.connect(
            self.update_duration
        )
        self.process_button.clicked.connect(
            self.process_audio
        )

        self.transcribe_button.clicked.connect(
            self.process_and_transcribe
        )
        self.position_slider.sliderMoved.connect(
            self.seek_audio
        )
        self.waveform_widget.seek_requested.connect(
            self.seek_audio
        )
        self.trim_checkbox.toggled.connect(
            self.on_trim_toggled
        )

        self.trim_start_edit.editingFinished.connect(
            self.on_trim_changed
        )

        self.trim_end_edit.editingFinished.connect(
            self.on_trim_changed
        )
        self.silence_checkbox.toggled.connect(
            self.on_silence_toggled
        )

        self.silence_threshold_edit.editingFinished.connect(
            self.on_silence_changed
        )

        self.silence_duration_edit.editingFinished.connect(
            self.on_silence_changed
        )

    def on_trim_toggled(
        self,
        checked
    ):

        self.trim_start_edit.setEnabled(
            checked
        )

        self.trim_end_edit.setEnabled(
            checked
        )

        self.settings.trim_start_enabled = checked
        self.settings.trim_end_enabled = checked
        self.waveform_widget.update()

    def on_trim_changed(self):

        try:

            start_seconds = self.parse_time(
                self.trim_start_edit.text()
            )

            end_seconds = self.parse_time(
                self.trim_end_edit.text()
            )

            self.settings.trim_start_time = (
                start_seconds
            )

            self.settings.trim_end_time = (
                end_seconds
            )
            
            self.validate_trim_range()

            duration = (
                end_seconds
                - start_seconds
            )

            self.trim_duration_label.setText(
                "Durée conservée : "
                + self.format_time_ms(duration)
            )
            self.waveform_widget.update()
            
        except Exception:
            pass

    def parse_time(
        self,
        text
    ):

        h, m, s = text.split(":")

        return (
            int(h) * 3600
            + int(m) * 60
            + float(s)
        )

    def format_time_ms(
        self,
        seconds
    ):

        hours = int(seconds // 3600)

        minutes = int(
            (seconds % 3600) // 60
        )

        secs = seconds % 60

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{secs:06.3f}"
        )

    def validate_trim_range(self):

        if not hasattr(self, "duration"):
            return

        start_time = self.settings.trim_start_time
        end_time = self.settings.trim_end_time

        start_time = max(
            0.0,
            start_time
        )

        end_time = min(
            self.duration,
            end_time
        )

        if end_time <= start_time:

            if start_time >= self.duration:
                start_time = max(
                    0.0,
                    self.duration - 1
                )

            end_time = min(
                self.duration,
                start_time + 1
            )

        self.settings.trim_start_time = start_time
        self.settings.trim_end_time = end_time

        self.trim_start_edit.setText(
            self.format_time_ms(start_time)
        )

        self.trim_end_edit.setText(
            self.format_time_ms(end_time)
        )

        self.trim_duration_label.setText(
            "Durée conservée : "
            + self.format_time_ms(
                end_time - start_time
            )
        )

    def on_silence_toggled(
        self,
        checked
    ):

        self.settings.silence_enabled = checked

        self.silence_threshold_edit.setEnabled(
            checked
        )

        self.silence_duration_edit.setEnabled(
            checked
        )

    def on_silence_changed(
        self
    ):

        try:

            self.settings.silence_threshold_db = float(
                self.silence_threshold_edit.text()
            )

            self.settings.silence_min_duration = (
                float(
                    self.silence_duration_edit.text()
                )
                / 1000
            )

        except ValueError:
            pass

    def on_speed_changed(
        self,
        value
    ):
        self.settings.speed_percent = value
        self.speed_label.setText(
            f"+{value} %"
        )

    def process_audio(self):

        pipeline = (
            AudioProcessingPipeline(
                self.audio_file,
                self.working_wav,
                self.settings
            )
        )

        pipeline.run()

        print(
            "Pipeline terminé"
        )       

    def process_and_transcribe(self):

        self.transcribe_after_processing = True

        self.accept()

    def get_options(self):

        return {

            "trim_start_enabled":
                self.settings.trim_start_enabled,

            "trim_start_time":
                self.settings.trim_start_time,

            "trim_end_enabled":
                self.settings.trim_end_enabled,

            "trim_end_time":
                self.settings.trim_end_time,

            "silence_enabled":
                self.settings.silence_enabled,

            "silence_threshold_db":
                self.settings.silence_threshold_db,

            "silence_min_duration":
                self.settings.silence_min_duration,

            "speed_enabled":
                self.settings.speed_enabled,

            "speed_percent":
                self.settings.speed_percent,
        }

    def format_time(
        self,
        seconds
    ):

        minutes = int(seconds // 60)

        seconds = int(seconds % 60)

        return (
            f"{minutes:02}:{seconds:02}"
        )

    def update_duration(
        self,
        duration
    ):

        self.duration = duration

        self.position_slider.setMaximum(
            int(duration)
        )

        self.position_label.setText(
            f"00:00 / "
            f"{self.format_time(duration)}"
        )
        if self.trim_end_edit.text() == "00:00:00.000":

            self.trim_end_edit.setText(
                self.format_time_ms(duration)
            )

            self.trim_duration_label.setText(
                "Durée conservée : "
                + self.format_time_ms(duration)
            )

            self.settings.trim_end_time = duration
            self.settings.trim_start_time = 0.0
            
    def update_position(
        self,
        position
    ):

        self.position_slider.blockSignals(
            True
        )

        self.position_slider.setValue(
            int(position)
        )

        self.position_slider.blockSignals(
            False
        )

        self.position_label.setText(
            f"{self.format_time(position)} / "
            f"{self.format_time(self.duration)}"
        )

        if self.waveform_widget.document:

            document = (
                self.waveform_widget.document
            )

            document.current_time = position
            if getattr(
                document,
                "disable_auto_follow",
                False
            ):
                document.disable_auto_follow = False

                self.waveform_widget.update()

                return
            
            if document.zoom_factor > 1:

                visible_ratio = (
                    self.waveform_widget.get_visible_ratio()
                )

                current_ratio = (
                    position
                    / document.duration_seconds
                )

                document.view_offset = (
                    current_ratio
                    - visible_ratio / 2
                )

                document.view_offset = max(
                    0.0,
                    min(
                        1.0 - visible_ratio,
                        document.view_offset
                    )
                )

            self.waveform_widget.update()

    def seek_audio(
        self,
        position
    ):

        self.playback.set_position(
            position
        )

    def on_duration_changed(
        self,
        duration
    ):

        self.position_slider.setMaximum(
            duration
        )

    def on_position_changed(
        self,
        position
    ):

        self.position_slider.blockSignals(
            True
        )

        self.position_slider.setValue(
            position
        )
        if self.waveform_widget.document:

            self.waveform_widget.document.current_time = (
                position
            )

            self.waveform_widget.update()
        self.position_slider.blockSignals(
            False
        )

        seconds = position / 1000

        minutes = int(seconds // 60)

        sec = int(seconds % 60)

        self.position_slider.setText(
            f"{minutes:02}:{sec:02}"
        )

    def on_slider_moved(
        self,
        value
    ):

        self.player.setPosition(
            value
        )
    

