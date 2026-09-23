# ui/audio_preprocess_dialog.py

import wave
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
from services.silence_detection_service import SilenceDetectionService


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
        self.opacity_fade = 0.4
        self.trim_start_time = 0.0
        self.trim_end_time = 0.0
        self.detected_silences = []
        self.filtered_silences = []
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
            220
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
            "00:00:00.0"
        )

        self.trim_end_edit = QLineEdit(
            "00:00:00.0"
        )

        self.trim_duration_label = QLabel(
            "Durée conservée : 00:00:00"
        )
        self.trim_removed_label = QLabel(
            "Temps supprimé : 00:00:00"
        )
        self.trim_duration_label.setVisible(
            self.settings.trim_start_enabled
        )

        self.trim_removed_label.setVisible(
            self.settings.trim_start_enabled
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
            str(
                self.settings.silence_threshold_db
                )
        )

        self.silence_duration_edit = QLineEdit(
            str(
                self.settings.silence_min_duration
                )
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

        self.silence_count_label = QLabel(
            "Silences détectés : 0"
        )
        
        self.silence_total_label = QLabel(
            "Temps total des silences : 00:00:00"
        )
        self.silence_count_label.setVisible(
            self.settings.silence_enabled
        )

        self.silence_total_label.setVisible(
            self.settings.silence_enabled
        )

        self.speed_checkbox = QCheckBox(
            "Accélérer"
        )
        slider_width = 300
        self.speed_colorbar = QWidget()
        self.speed_colorbar.setFixedSize(slider_width, 8)
        self.speed_colorbar.setStyleSheet("""
        QWidget {
            border-radius: 4px;
            background: qlineargradient(
                x1:0, y1:0,
                x2:1, y2:0,
                stop:0.0 #4CAF50,
                stop:0.5 #4CAF50,
                stop:0.75 #FFA000,
                stop:1.0 #D32F2F
            );
        }
        """)

        self.speed_slider = QSlider(
            Qt.Horizontal
        )
        self.speed_slider.setFixedWidth(slider_width)

        self.speed_slider.setRange(
            0,
            100
        )

        self.speed_slider.setValue(
            self.settings.speed_percent
        )

        self.speed_slider.setEnabled(
            False
        )

        self.speed_ratio_label = QLabel(
            f"{1 + self.settings.speed_percent / 100:.2f}x"
        )
        self.speed_gain_label = QLabel(
            "Gain théorique : 00:00:00"
        )
    

        self.summary_original_label = QLabel(
            "Durée originale : 00:00:00"
        )

        self.summary_removed_label = QLabel(
            "Temps supprimé : 00:00:00"
        )

        self.summary_final_label = QLabel(
            "Durée finale estimée : 00:00:00"
        )
        self.summary_ratio_label = QLabel(
        "Optimisation : 0 %"
        )


        self.speed_gain_label.setVisible(
            self.settings.speed_enabled
        )

        self.speed_ratio_label.setEnabled(
            False
        )

        self.speed_checkbox.setChecked(
            self.settings.speed_enabled
        )

        self.speed_slider.setEnabled(
            self.settings.speed_enabled
        )

        self.speed_ratio_label.setEnabled(
            self.settings.speed_enabled
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

        self.trim_start_label = QLabel(
        "Début :"
        )
        
        trim_values_layout.addWidget(
        self.trim_start_label
        )

        trim_values_layout.addWidget(
            self.trim_start_edit
        )

        trim_values_layout.addSpacing(
            20
        )

        self.trim_end_label = QLabel(
            "Fin :"
        )

        trim_values_layout.addWidget(
            self.trim_end_label
        )

        trim_values_layout.addWidget(
            self.trim_end_edit
        )

        trim_values_layout.addSpacing(
            20
        )

        trim_values_layout.addWidget(
            self.trim_duration_label
        )

        trim_values_layout.addSpacing(
            20
        )

        trim_values_layout.addWidget(
            self.trim_removed_label
        )

        trim_values_layout.addStretch()

        trim_layout.addLayout(
            trim_values_layout
        )

        effects_layout.addLayout(
            trim_layout
        )

        silence_layout = QVBoxLayout()

        silence_layout.addWidget(
            self.silence_checkbox
        )

        silence_params_layout = QHBoxLayout()

        self.silence_threshold_label = QLabel(
            "Seuil (dB) :"
        )

        silence_params_layout.addWidget(
            self.silence_threshold_label
        )

        silence_params_layout.addWidget(
            self.silence_threshold_edit
        )

        silence_params_layout.addSpacing(
            20
        )

        self.silence_duration_label = QLabel(
            "Durée mini (s) :"
        )

        silence_params_layout.addWidget(
            self.silence_duration_label
        )

        silence_params_layout.addWidget(
            self.silence_duration_edit
        )
        silence_params_layout.addSpacing(
            30
        )

        silence_params_layout.addWidget(
            self.silence_count_label
        )

        silence_params_layout.addSpacing(
            20
        )

        silence_params_layout.addWidget(
            self.silence_total_label
        )

        silence_params_layout.addStretch()

        silence_layout.addLayout(
            silence_params_layout
        )

        effects_layout.addLayout(
            silence_layout
        )

        speed_layout = QVBoxLayout()

        speed_layout.addWidget(
            self.speed_checkbox
        )
        self.speed_colorbar.setWindowOpacity(
            0.25
        )
        
        speed_layout.addWidget(
            self.speed_colorbar,
            alignment=Qt.AlignLeft
        )

        slider_layout = QHBoxLayout()

        slider_layout.addWidget(
            self.speed_slider
        )

        slider_layout.addWidget(
            self.speed_ratio_label
        )

        slider_layout.addSpacing(
            20
        )

        slider_layout.addWidget(
            self.speed_gain_label
        )

        slider_layout.addStretch()

        speed_layout.addLayout(
            slider_layout
        )

        effects_layout.addLayout(
            speed_layout
        )

        effects_layout.addStretch()

        separator = QLabel(
            "────────────────────────────────────────────"
        )

        effects_layout.addWidget(
            separator
        )

        summary_layout = QHBoxLayout()

        summary_layout.addWidget(
            self.summary_original_label
        )

        summary_layout.addSpacing(
            20
        )

        summary_layout.addWidget(
            self.summary_removed_label
        )

        summary_layout.addSpacing(
            20
        )

        summary_layout.addWidget(
            self.summary_final_label
        )

        summary_layout.addSpacing(
            20
        )

        summary_layout.addWidget(
            self.summary_ratio_label
        )

        summary_layout.addStretch()

        effects_layout.addLayout(
            summary_layout
        )
        
        
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

        self.trim_start_label.setEnabled(
            self.settings.trim_start_enabled
        )

        self.trim_end_label.setEnabled(
            self.settings.trim_start_enabled
        )

        self.silence_threshold_label.setEnabled(
            self.settings.silence_enabled
        )

        self.silence_duration_label.setEnabled(
            self.settings.silence_enabled
        )
        
        self.on_trim_toggled(
            self.settings.trim_start_enabled
        )

        self.on_silence_toggled(
            self.settings.silence_enabled
        )

        self.on_speed_toggled(
            self.settings.speed_enabled
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
            200,
            400,
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
        self.speed_checkbox.toggled.connect(
            self.on_speed_toggled
        )

        self.speed_slider.valueChanged.connect(
            self.on_speed_changed
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
        self.trim_duration_label.setVisible(
            checked
        )

        self.trim_removed_label.setVisible(
            checked
        )

        for widget in [
            self.trim_start_label,
            self.trim_end_label,

        ]:
            widget.setEnabled(
                checked
            )
        self.settings.trim_start_enabled = checked
        self.settings.trim_end_enabled = checked
        self.waveform_widget.update()
        self.update_summary()

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
                + self.format_duration(duration)
            )
            self.update_filtered_silences()
            self.waveform_widget.update()
            self.update_analysis()
            self.update_summary()
            
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

    def format_time_tenth(
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
            f"{secs:04.1f}"
        )


    def format_duration(
        self,
        seconds
    ):

        total = int(seconds)

        hours = total // 3600

        minutes = (
            total % 3600
        ) // 60

        secs = total % 60

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{secs:02d}"
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
            self.format_time_tenth(start_time)
        )

        self.trim_end_edit.setText(
            self.format_time_tenth(end_time)
        )

        self.trim_duration_label.setText(
            "Durée conservée : "
            + self.format_duration(
                end_time - start_time
            )
        )

    def on_silence_toggled(
        self,
        checked
    ):

        self.settings.silence_enabled = checked
        if checked:
            
            self.on_silence_changed()
            
        else:
            
            self.detected_silences = []
            
            self.waveform_widget.update()

        self.waveform_widget.update()
        self.silence_threshold_edit.setEnabled(
            checked
        )

        self.silence_duration_edit.setEnabled(
            checked
        )

        self.silence_count_label.setVisible(
            checked
        )

        self.silence_total_label.setVisible(
            checked
        )
        self.update_summary()



    def on_silence_changed(
        self
    ):

        try:

            self.settings.silence_threshold_db = float(
                self.silence_threshold_edit.text()
            )

            self.settings.silence_min_duration = float(
                    self.silence_duration_edit.text()
            )
            

            try:

                detector = (
                    SilenceDetectionService()
                )

                self.detected_silences = (
                    detector.detect_silences(
                        self.working_wav,
                        self.settings.silence_threshold_db,
                        self.settings.silence_min_duration
                    )
                )

                self.waveform_widget.update()
                self.update_filtered_silences()
                self.update_analysis()
                self.update_summary()

            except Exception:

                self.detected_silences = []


        except ValueError:
            pass
        

    def on_speed_toggled(
        self,
        checked
    ):

        self.settings.speed_enabled = checked

        self.speed_slider.setEnabled(
            checked
        )

        self.speed_ratio_label.setEnabled(
            checked
        )

        self.speed_gain_label.setVisible(
            checked
        )
        
        if checked:

            self.speed_colorbar.setStyleSheet("""
            QWidget {
                border-radius: 4px;
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:1, y2:0,
                    stop:0.0 #4CAF50,
                    stop:0.5 #4CAF50,
                    stop:0.75 #FFA000,
                    stop:1.0 #D32F2F
                );
            }
            """)

        else:

            self.speed_colorbar.setStyleSheet("""
            QWidget {
                border-radius: 4px;
                background: rgba(255,255,255,30);
            }
            """)
        self.update_summary()


    def on_speed_changed(
        self,
        value
    ):

        self.settings.speed_percent = value

        self.speed_ratio_label.setText(
            f"{1 + value / 100:.2f}x"
        )
        self.update_analysis()
        self.update_summary()

    def update_summary(self):

        if not hasattr(
            self,
            "duration"
        ):
            return

        original_duration = self.duration

        trim_removed = 0.0
        silence_removed = 0.0

        #
        # Découpe
        #
        trimmed_duration = original_duration

        if self.settings.trim_start_enabled:

            trim_removed = (
                self.settings.trim_start_time
                +
                (
                    original_duration
                    - self.settings.trim_end_time
                )
            )

            trimmed_duration = max(
                0,
                original_duration
                - trim_removed
            )

        #
        # Silences
        #
        if self.settings.silence_enabled:

            silence_removed = sum(
                end - start
                for start, end
                in self.filtered_silences
            )

        after_silence_duration = max(
            0,
            trimmed_duration
            - silence_removed
        )

        #
        # Accélération
        #
        final_duration = (
            after_silence_duration
        )

        if self.settings.speed_enabled:

            ratio = (
                1.0
                + self.settings.speed_percent / 100
            )

            final_duration = (
                after_silence_duration
                / ratio
            )

            speed_gain = (
                after_silence_duration
                - final_duration
            )

        else:

            speed_gain = 0.0

        #
        # Résumé
        #
        total_removed = (
            original_duration
            - final_duration
        )

        optimization_percent = 0

        if original_duration > 0:

            optimization_percent = (
                total_removed
                / original_duration
                * 100
            )

        self.summary_original_label.setText(
            "Durée originale : "
            + self.format_duration(
                original_duration
            )
        )

        self.summary_removed_label.setText(
            "Temps supprimé : "
            + self.format_duration(
                total_removed
            )
        )

        self.summary_final_label.setText(
            "Durée finale estimée : "
            + self.format_duration(
                final_duration
            )
        )

        self.summary_ratio_label.setText(
            f"Optimisation : "
            f"{optimization_percent:.1f} %"
        )

        #
        # Détails découpe
        #
        self.trim_removed_label.setText(
            "Temps supprimé : "
            + self.format_duration(
                trim_removed
            )
        )

        #
        # Détails silences
        #
        self.silence_count_label.setText(
            f"Silences détectés : "
            f"{len(self.filtered_silences)}"
        )

        self.silence_total_label.setText(
            "Temps total des silences : "
            + self.format_duration(
                silence_removed
            )
        )

        #
        # Détails accélération
        #
        self.speed_gain_label.setText(
            "Gain théorique : "
            + self.format_duration(
                speed_gain
            )
        )

    def update_analysis(self):

        if not hasattr(
            self,
            "duration"
        ):
            return

        #
        # Durée originale
        #

        original_duration = self.duration

        #
        # Trim
        #

        trim_removed = 0.0

        duration_after_trim = (
            original_duration
        )

        if self.settings.trim_start_enabled:

            trim_removed = (
                self.settings.trim_start_time
                +
                (
                    original_duration
                    - self.settings.trim_end_time
                )
            )

            duration_after_trim = max(
                0.0,
                original_duration
                - trim_removed
            )

        #
        # Silences
        #

        silence_removed = 0.0

        silence_count = 0

        if self.settings.silence_enabled:

            filtered_silences = []

            trim_start = (
                self.settings.trim_start_time
                if self.settings.trim_start_enabled
                else 0.0
            )

            trim_end = (
                self.settings.trim_end_time
                if self.settings.trim_start_enabled
                else original_duration
            )

            for start, end in self.filtered_silences:

                if end <= trim_start:
                    continue

                if start >= trim_end:
                    continue

                visible_start = max(
                    start,
                    trim_start
                )

                visible_end = min(
                    end,
                    trim_end
                )

                filtered_silences.append(
                    (
                        visible_start,
                        visible_end
                    )
                )

            silence_count = len(
                self.filtered_silences
            )

            silence_removed = sum(
                end - start
                for start, end
                in self.filtered_silences
            )

        duration_after_silence = max(
            0.0,
            duration_after_trim
            - silence_removed
        )

        #
        # Vitesse
        #

        speed_gain = 0.0

        final_duration = (
            duration_after_silence
        )

        if self.settings.speed_enabled:

            ratio = (
                1
                + self.settings.speed_percent / 100
            )

            final_duration = (
                duration_after_silence
                / ratio
            )

            speed_gain = (
                duration_after_silence
                - final_duration
            )

        #
        # Résumé
        #

        total_removed = (
            trim_removed
            + silence_removed
            + speed_gain
        )

        optimization = 0.0

        if original_duration > 0:

            optimization = (
                total_removed
                / original_duration
                * 100
            )

        #
        # UI Trim
        #

        self.trim_removed_label.setText(
            "Temps supprimé : "
            + self.format_duration(
                trim_removed
            )
        )

        #
        # UI Silence
        #

        self.silence_count_label.setText(
            f"Silences détectés : "
            f"{silence_count}"
        )

        self.silence_total_label.setText(
            "Temps total des silences : "
            + self.format_duration(
                silence_removed
            )
        )

        #
        # UI Speed
        #

        self.speed_gain_label.setText(
            "Gain théorique : "
            + self.format_duration(
                speed_gain
            )
        )

        #
        # Résumé final
        #

        self.summary_original_label.setText(
            "Durée originale : "
            + self.format_duration(
                original_duration
            )
        )

        self.summary_removed_label.setText(
            "Temps supprimé : "
            + self.format_duration(
                total_removed
            )
        )

        self.summary_final_label.setText(
            "Durée finale : "
            + self.format_duration(
                final_duration
            )
        )

        self.summary_ratio_label.setText(
            f"Optimisation : "
            f"{optimization:.1f} %"
        )

    def update_filtered_silences(self):

        trim_start = 0.0
        trim_end = self.duration

        if self.settings.trim_start_enabled:

            trim_start = (
                self.settings.trim_start_time
            )

            trim_end = (
                self.settings.trim_end_time
            )

        self.filtered_silences = []

        for start, end in self.detected_silences:

            if end <= trim_start:
                continue

            if start >= trim_end:
                continue

            self.filtered_silences.append(
                (
                    max(start, trim_start),
                    min(end, trim_end)
                )
            )
        self.update_analysis()

    def get_wav_duration(
        self,
        wav_file
    ):
        with wave.open(
            str(wav_file),
            "rb"
        ) as wav:

            return (
                wav.getnframes()
                / wav.getframerate()
            )
        
    def process_audio(self):

        pipeline = (
            AudioProcessingPipeline(
                self.audio_file,
                self.working_wav,
                self.settings
            )
        )

        output_file = pipeline.run()

        real_duration = (
            self.get_wav_duration(
                output_file
            )
        )

        original_duration = (
            self.duration
        )

        removed_time = (
            original_duration
            - real_duration
        )

        optimization = 0.0

        if original_duration > 0:

            optimization = (
                removed_time
                / original_duration
                * 100
            )

        self.summary_original_label.setText(
            "Durée originale : "
            + self.format_duration(
                original_duration
            )
        )

        self.summary_removed_label.setText(
            "Temps supprimé : "
            + self.format_duration(
                removed_time
            )
        )

        self.summary_final_label.setText(
            "Durée finale : "
            + self.format_duration(
                real_duration
            )
        )

        self.summary_ratio_label.setText(
            f"Optimisation : "
            f"{optimization:.1f} %"
        )

        print(
            f"Pipeline terminé : {output_file}"
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
        if self.settings.trim_end_time == 0:

            self.trim_end_edit.setText(
                self.format_time_tenth(duration)
            )

            self.trim_duration_label.setText(
                "Durée conservée : "
                + self.format_duration(duration)
            )

            self.settings.trim_end_time = duration
            self.settings.trim_start_time = 0.0
            self.update_analysis()
            self.update_summary()
            self.summary_original_label.setText(
                "Durée originale : "
                + self.format_duration(duration)
            )

            self.summary_final_label.setText(
                "Durée finale estimée : "
                + self.format_duration(duration)
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

    def on_slider_moved(
        self,
        value
    ):

        self.player.setPosition(
            value
        )
    

