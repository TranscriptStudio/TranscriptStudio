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
)
from PySide6.QtMultimedia import (
    QMediaPlayer,
    QAudioOutput
)

from PySide6.QtCore import Qt, QUrl
from pathlib import Path

from models.audio_processing_settings import (AudioProcessingSettings)
from services.playback import PlaybackManager
from services.audio_waveform_service import AudioWaveformService
from ui.waveform_widget import WaveformWidget

class AudioPreprocessDialog(QDialog):

    def __init__(
        self,
        audio_file,
        parent=None
    ):

        super().__init__(parent)
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
        self.cut_checkbox = QCheckBox(
            "Couper avant la position courante"
        )

        self.silence_checkbox = QCheckBox(
            "Supprimer les silences"
        )

        self.speed_checkbox = QCheckBox(
            "Accélérer"
        )
        effects_layout.addWidget(
            effects_title  
        )
        effects_layout.addWidget(
            self.cut_checkbox
        )

        effects_layout.addWidget(
            self.silence_checkbox
        )

        effects_layout.addWidget(
            self.speed_checkbox
        )
        effects_layout.addStretch()
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
        
    def on_speed_changed(
        self,
        value
    ):
        self.settings.speed_percent = value
        self.speed_label.setText(
            f"+{value} %"
        )

    def process_audio(self):

        self.accept()       

    def process_and_transcribe(self):

        self.transcribe_after_processing = True

        self.accept()

    def get_options(self):

        return {

            "cut_before_enabled":
                self.cut_checkbox.isChecked(),

            "remove_silence_enabled":
                self.silence_checkbox.isChecked(),

            "speed_enabled":
                self.speed_checkbox.isChecked(),

            "speed_percent":
                self.settings.speed_percent,

            "cut_before_seconds":
                self.settings.cut_before_seconds
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

        self.settings.cut_before_seconds = (
            seconds
        )

    def on_slider_moved(
        self,
        value
    ):

        self.player.setPosition(
            value
        )
    

