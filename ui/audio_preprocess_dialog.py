# ui/audio_preprocess_dialog.py

import wave
import shutil
import time

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
    QProgressDialog,
    QMessageBox,
)
from PySide6.QtMultimedia import (
    QMediaPlayer,
    QAudioOutput
)

from PySide6.QtCore import Qt, QUrl, QThread
from pathlib import Path

from models.audio_processing_settings import AudioProcessingSettings

from services.playback import PlaybackManager
from services.audio_waveform_service import AudioWaveformService
from services.audio_processing_pipeline import  AudioProcessingPipeline
from services.silence_detection_service import SilenceDetectionService
from services.audio_processing_worker import AudioProcessingWorker
from services.ffmpeg_paths import FFMPEG_PATH
from services.audio_finalization_worker import AudioFinalizationWorker

from ui.waveform_widget import WaveformWidget

class AudioPreprocessDialog(QDialog):

    def __init__(
        self,
        audio_file,
        project_folder,
        audio_document=None,
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
        self.removal_silences = []
        self.setWindowFlag(
            Qt.WindowMinMaxButtonsHint,
            True
        )
        self.setWindowModality(
            Qt.WindowModal
        )
        self.audio_file = audio_file
        self.audio_document = (
            audio_document
        )
        self.project_folder = Path(
            project_folder
        )

        self.processed_audio_file = None

        self.settings = (
            AudioProcessingSettings()
        )

        self.playback = PlaybackManager()

        self.playback.load_file(self.audio_file)
        self.result_playback = PlaybackManager()
        self.result_duration = 0.0
        self.processing_progress = None
        self.processing_thread = None
        self.processing_worker = None

        self.finalization_progress = None
        self.finalization_thread = None
        self.finalization_worker = None

        self.preprocessing_validated = False

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

        if self.audio_document is not None:
            self.waveform_widget.set_document(
                self.audio_document
            )
        else:
            self.waveform_widget.load_audio(
                self.audio_file
            )

        self.processing_wav = (
            self.waveform_widget.document.processing_wav
        )
        

        self.waveform_widget.setMinimumHeight(
            80
        )

        toolbar = QHBoxLayout()

        self.play_button = QPushButton("▶")
        self.play_button.setToolTip("Lecture du fichier origine")

        self.pause_button = QPushButton("⏸")
        self.pause_button.setToolTip("Mettre en pause")

        self.stop_button = QPushButton("⏹")
        self.stop_button.setToolTip("Arrêter la lecture")

        self.zoom_in_button = QPushButton("➕")
        self.zoom_in_button.setToolTip("Zoom avant de la piste")

        self.zoom_out_button = QPushButton("➖")
        self.zoom_out_button.setToolTip("Zoom arrière de la piste")

        self.fit_button = QPushButton("↔️")
        self.fit_button.setToolTip("Revenir à l'affichage complet de la piste")

        self.process_button = QPushButton("✨ Lancer le traitement")
        self.process_button.setToolTip("Lance le traitement des effets sélectionnées")

        self.transcribe_button = QPushButton("☁ Transcrire")
        self.transcribe_button.setEnabled(
            False
        )
        self.transcribe_button.setToolTip(
        "Lancez d'abord le traitement audio "
        "pour pouvoir utiliser le fichier traité "
        "pour la transcription."
    )
        for btn in [
            self.play_button,
            self.pause_button,
            self.stop_button,
            self.zoom_in_button,
            self.zoom_out_button,
            self.fit_button,
            self.process_button,
            self.transcribe_button,
        ]:

            btn.setFixedSize(40, 40)
            if btn == self.process_button:
                btn.setFixedSize(150, 40)
            if btn == self.transcribe_button:
                            btn.setFixedSize(100, 40)
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
        effects_title = QLabel(
            "Options de traitement"
        )

        effects_title.setStyleSheet("""
            font-weight: bold;
            font-size: 16px;
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
        self.silence_buffer_edit = QLineEdit(
            str(
                self.settings.silence_buffer_duration
            )
        )

        self.silence_threshold_edit.setFixedWidth(
            80
        )

        self.silence_duration_edit.setFixedWidth(
            80
        )
        self.silence_buffer_edit.setFixedWidth(
            80
        )

        self.silence_threshold_edit.setEnabled(
            False
        )

        self.silence_duration_edit.setEnabled(
            False
        )
        self.silence_buffer_edit.setEnabled(
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
            20
        )

        self.silence_buffer_label = QLabel(
            "Buffer (s) :"
        )

        silence_params_layout.addWidget(
            self.silence_buffer_label
        )

        silence_params_layout.addWidget(
            self.silence_buffer_edit
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

        #
        # Résultat du traitement
        #
        self.result_panel = QWidget()

        result_layout = QVBoxLayout(
            self.result_panel
        )

        result_layout.setContentsMargins(
            0,
            14,
            0,
            0
        )

        result_layout.setSpacing(
            6
        )

        self.result_title = QLabel(
            "Résultat du traitement"
        )

        self.result_title.setStyleSheet("""
            font-weight: bold;
            font-size: 16px;
        """)

        result_layout.addWidget(
            self.result_title
        )

        self.result_waveform_widget = (
            WaveformWidget(
                show_processing_overlays=False,
                waveform_color="#F39C12"
            )
        )

        self.result_waveform_widget.setMinimumHeight(
            100
        )

        result_layout.addWidget(
            self.result_waveform_widget
        )
        #
        # Commandes de lecture du résultat
        #
        result_controls_layout = QHBoxLayout()

        self.result_play_button = QPushButton(
            "▶"
        )

        self.result_stop_button = QPushButton(
            "⏹"
        )

        self.result_position_slider = QSlider(
            Qt.Horizontal
        )

        self.result_position_label = QLabel(
            "00:00 / 00:00"
        )

        self.result_play_button.setFixedSize(
            36,
            30
        )

        self.result_stop_button.setFixedSize(
            36,
            30
        )

        self.result_position_label.setFixedWidth(
            90
        )

        result_controls_layout.addWidget(
            self.result_play_button
        )

        result_controls_layout.addWidget(
            self.result_stop_button
        )

        result_controls_layout.addWidget(
            self.result_position_slider,
            1
        )

        result_controls_layout.addWidget(
            self.result_position_label
        )

        result_layout.addLayout(
            result_controls_layout
        )
        effects_layout.addWidget(
            self.result_panel
        )
        effects_layout.addStretch()

        self.result_panel.setVisible(
            False
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

        self.silence_buffer_label.setEnabled(
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
            120,
            480,
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

        self.silence_buffer_edit.editingFinished.connect(
            self.on_silence_changed
        )

        self.speed_checkbox.toggled.connect(
            self.on_speed_toggled
        )

        self.speed_slider.valueChanged.connect(
            self.on_speed_changed
        )
        #
        # Lecteur du résultat
        #
        self.result_play_button.clicked.connect(
            self.result_playback.toggle_play_pause
        )

        self.result_stop_button.clicked.connect(
            self.result_playback.stop
        )

        self.result_playback.position_changed.connect(
            self.update_result_position
        )

        self.result_playback.duration_changed.connect(
            self.update_result_duration
        )

        self.result_playback.playing_changed.connect(
            self.update_result_play_button
        )

        self.result_position_slider.sliderMoved.connect(
            self.seek_result_audio
        )

        self.result_waveform_widget.seek_requested.connect(
            self.seek_result_audio
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

        self.silence_buffer_edit.setEnabled(
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
            self.settings.silence_buffer_duration = max(
                0.0,
                float(
                    self.silence_buffer_edit.text()
                )
            )

            try:

                detector = (
                    SilenceDetectionService()
                )

                self.detected_silences = (
                    detector.detect_silences(
                        self.waveform_widget.document.display_wav,
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
        #
        # Eviter plusieurs traitements simultanés.
        #
        if (
            hasattr(self, "processing_thread")
            and self.processing_thread is not None
        ):
            return

        #
        # Réinitialisation de l'ancien résultat.
        #
        self.result_playback.stop()
        self.result_playback.set_position(
            0.0
        )

        self.result_position_slider.blockSignals(
            True
        )
        self.result_position_slider.setValue(
            0
        )
        self.result_position_slider.blockSignals(
            False
        )

        self.result_position_label.setText(
            "00:00 / 00:00"
        )

        self.result_duration = 0.0

        output_file = (
            self.project_folder
            / "audio_processed.wav"
        )

        #
        # Popup de progression.
        #
        self.processing_progress = QProgressDialog(
            "Préparation du traitement...",
            "",
            0,
            100,
            self
        )

        self.processing_progress.setWindowTitle(
            "Traitement audio"
        )

        self.processing_progress.setWindowModality(
            Qt.WindowModal
        )

        self.processing_progress.setCancelButton(
            None
        )

        self.processing_progress.setMinimumDuration(
            0
        )

        self.processing_progress.setAutoClose(
            False
        )

        self.processing_progress.setAutoReset(
            False
        )

        self.processing_progress.setValue(
            0
        )

        #
        # Thread.
        #
        self.processing_thread = QThread(
            self
        )

        #
        # Worker.
        #
        self.processing_worker = (
            AudioProcessingWorker(
                self.audio_file,
                self.processing_wav,
                self.settings,
                output_file
            )
        )

        self.processing_worker.moveToThread(
            self.processing_thread
        )

        #
        # Démarrage.
        #
        self.processing_thread.started.connect(
            self.processing_worker.run
        )

        #
        # Progression.
        #
        self.processing_worker.progress.connect(
            self.update_processing_progress
        )

        #
        # Fin correcte.
        #
        self.processing_worker.finished.connect(
            self.processing_finished
        )

        self.processing_worker.finished.connect(
            self.processing_thread.quit
        )

        #
        # Erreur.
        #
        self.processing_worker.error.connect(
            self.processing_error
        )

        self.processing_worker.error.connect(
            self.processing_thread.quit
        )

        #
        # Nettoyage Qt.
        #
        self.processing_thread.finished.connect(
            self.processing_worker.deleteLater
        )

        self.processing_thread.finished.connect(
            self.cleanup_processing
        )

        #
        # Empêcher un second lancement.
        #
        self.process_button.setEnabled(
            False
        )

        #
        # Afficher puis démarrer.
        #
        self.processing_progress.show()

        self.processing_thread.start()

    def update_processing_progress(
        self,
        value,
        message
    ):
        if self.processing_progress is None:
            return

        self.processing_progress.setLabelText(
            message
        )

        self.processing_progress.setValue(
            value
        )

    def processing_finished(
        self,
        output_file,
        document
    ):
        #
        # Nouveau fichier traité.
        #
        self.processed_audio_file = (
            output_file
        )
        self.transcribe_button.setEnabled(
            True
        )
        self.transcribe_button.setToolTip(
            "Utiliser le fichier audio traité "
            "pour poursuivre vers la transcription."
        )

        #
        # Le document de waveform a déjà été
        # calculé dans le worker.
        #
        self.result_waveform_widget.set_document(
            document
        )

        self.result_waveform_widget.document.current_time = (
            0.0
        )

        self.result_waveform_widget.fit_all()

        self.result_waveform_widget.set_display_duration(
            self.duration
        )

        #
        # Lecteur résultat.
        #
        self.result_playback.load_file(
            str(
                self.processed_audio_file
            )
        )

        self.result_playback.set_position(
            0.0
        )

        #
        # Afficher le résultat.
        #
        self.result_panel.setVisible(
            True
        )

        #
        # Statistiques réelles.
        #
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

        if self.processing_progress is not None:
            self.processing_progress.setValue(
                100
            )
            self.processing_progress.close()

        print(
            f"Pipeline terminé : {output_file}"
        )
    
    def processing_error(
        self,
        message
    ):
        if self.processing_progress is not None:
            self.processing_progress.close()

        QMessageBox.critical(
            self,
            "Erreur de traitement",
            (
                "Impossible de traiter "
                "le fichier audio.\n\n"
                + message
            )
        )

    def cleanup_processing(self):
        self.process_button.setEnabled(
            True
        )

        self.processing_progress = None
        self.processing_thread = None
        self.processing_worker = None

    def process_and_transcribe(self):
        if self.processed_audio_file is None:
            return

        if self.finalization_thread is not None:
            return

        #
        # Arrêter les deux lecteurs.
        #
        self.playback.stop()
        self.result_playback.stop()

        #
        # Désactiver Transcrire pour éviter
        # un double lancement.
        #
        self.transcribe_button.setEnabled(
            False
        )

        #
        # Popup indéterminé.
        #
        self.finalization_progress = (
            QProgressDialog(
                (
                    "Finalisation du fichier audio...\n"
                    "Veuillez patienter."
                ),
                "",
                0,
                0,
                self
            )
        )

        self.finalization_progress.setWindowTitle(
            "Finalisation audio"
        )

        self.finalization_progress.setWindowModality(
            Qt.WindowModal
        )

        self.finalization_progress.setCancelButton(
            None
        )

        self.finalization_progress.setMinimumDuration(
            0
        )

        self.finalization_progress.setRange(
            0,
            0
        )

        self.finalization_progress.setAutoClose(
            False
        )

        self.finalization_progress.setAutoReset(
            False
        )

        #
        # Thread.
        #
        self.finalization_thread = QThread(
            self
        )

        #
        # Worker.
        #
        self.finalization_worker = (
            AudioFinalizationWorker(
                self.processed_audio_file,
                self.audio_file,
                self.project_folder
            )
        )

        self.finalization_worker.moveToThread(
            self.finalization_thread
        )

        #
        # Démarrage.
        #
        self.finalization_thread.started.connect(
            self.finalization_worker.run
        )

        #
        # Fin correcte.
        #
        self.finalization_worker.finished.connect(
            self.finalization_finished
        )

        self.finalization_worker.finished.connect(
            self.finalization_thread.quit
        )

        #
        # Erreur.
        #
        self.finalization_worker.error.connect(
            self.finalization_error
        )

        self.finalization_worker.error.connect(
            self.finalization_thread.quit
        )

        #
        # Nettoyage Qt.
        #
        self.finalization_thread.finished.connect(
            self.finalization_worker.deleteLater
        )

        self.finalization_thread.finished.connect(
            self.cleanup_finalization
        )

        #
        # Afficher avant de démarrer.
        #
        self.finalization_progress.show()

        self.finalization_thread.start()

    def finalization_finished(
        self,
        final_file
    ):
        #
        # Fermer le popup.
        #
        if self.finalization_progress is not None:
            self.finalization_progress.close()

        #
        # Le fichier compressé devient
        # le fichier final officiel.
        #
        self.processed_audio_file = Path(
            final_file
        )

        #
        # Libérer audio_processed.wav
        # du lecteur résultat avant suppression.
        #
        self.result_playback.unload()

        #
        # Libérer également l'original.
        #
        self.playback.unload()

        #
        # La conversion finale étant validée,
        # supprimer tous les WAV temporaires.
        #
        failed_files = (
            self.cleanup_temporary_wav_files()
        )

        if failed_files:
            QMessageBox.warning(
                self,
                "Nettoyage incomplet",
                (
                    "Le fichier audio final a bien été créé, "
                    "mais certains fichiers temporaires "
                    "n'ont pas pu être supprimés.\n\n"
                    "Ils pourront être supprimés "
                    "ultérieurement."
                )
            )

        #
        # Le prétraitement est maintenant
        # officiellement validé.
        #
        self.preprocessing_validated = True
        #
        # Fermer le dialogue avec succès.
        #
        self.accept()

    def finalization_error(
        self,
        message
    ):
        if self.finalization_progress is not None:
            self.finalization_progress.close()

        self.transcribe_button.setEnabled(
            True
        )

        QMessageBox.critical(
            self,
            "Erreur de finalisation",
            (
                "Impossible de finaliser "
                "le fichier audio traité.\n\n"
                + message
            )
        )

    def cleanup_finalization(self):
        self.finalization_progress = None
        self.finalization_thread = None
        self.finalization_worker = None

    def get_processed_audio_file(self):
        #
        # Aucun fichier ne doit sortir du dialogue
        # tant que le prétraitement n'a pas été
        # officiellement validé.
        #
        if not self.preprocessing_validated:
            return None

        if self.processed_audio_file is None:
            return None

        processed_file = Path(
            self.processed_audio_file
        )

        #
        # Sécurité : le WAV de travail temporaire
        # ne doit jamais être transmis au workflow
        # de transcription.
        #
        temporary_wav = (
            self.project_folder
            / "audio_processed.wav"
        )

        if processed_file == temporary_wav:
            return None

        #
        # Le fichier final doit réellement exister.
        #
        if not processed_file.exists():
            return None

        return str(
            processed_file
        )

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
                
            "silence_buffer_duration":
                self.settings.silence_buffer_duration,
            
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

    def seek_result_audio(
        self,
        position
    ):
        self.result_playback.set_position(
            position
        )


    def update_result_duration(
        self,
        duration
    ):
        self.result_duration = duration

        self.result_position_slider.setMaximum(
            int(duration)
        )

        self.result_position_label.setText(
            "00:00 / "
            + self.format_time(duration)
        )


    def update_result_position(
        self,
        position
    ):
        self.result_position_slider.blockSignals(
            True
        )

        self.result_position_slider.setValue(
            int(position)
        )

        self.result_position_slider.blockSignals(
            False
        )

        self.result_position_label.setText(
            self.format_time(position)
            + " / "
            + self.format_time(
                self.result_duration
            )
        )

        if (
            self.result_waveform_widget.document
            is not None
        ):
            self.result_waveform_widget.document.current_time = (
                position
            )

            self.result_waveform_widget.update()


    def update_result_play_button(
        self,
        playing
    ):
        if playing:
            self.result_play_button.setText(
                "⏸"
            )
        else:
            self.result_play_button.setText(
                "▶"
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

    def closeEvent(self, event):
        #
        # Si le prétraitement a été validé
        # par Transcrire, ne rien supprimer.
        #
        if self.preprocessing_validated:
            event.accept()
            return

        #
        # Ne pas autoriser la fermeture pendant
        # un traitement audio en cours.
        #
        if self.processing_thread is not None:
            QMessageBox.information(
                self,
                "Traitement en cours",
                (
                    "Le traitement audio est "
                    "actuellement en cours.\n\n"
                    "Veuillez attendre sa fin "
                    "avant de fermer cette fenêtre."
                )
            )

            event.ignore()
            return

        #
        # Ne pas autoriser la fermeture pendant
        # la finalisation du fichier.
        #
        if self.finalization_thread is not None:
            QMessageBox.information(
                self,
                "Finalisation en cours",
                (
                    "La finalisation du fichier audio "
                    "est actuellement en cours.\n\n"
                    "Veuillez attendre sa fin."
                )
            )

            event.ignore()
            return

        #
        # Demander confirmation avant abandon.
        #
        reply = QMessageBox.question(
            self,
            "Abandonner le prétraitement",
            (
                "Voulez-vous vraiment abandonner "
                "le prétraitement audio ?\n\n"
                "Le projet provisoire et les fichiers "
                "générés seront supprimés."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            event.ignore()
            return

        try:
            self.cleanup_abandoned_preprocessing()

        except OSError as e:
            QMessageBox.critical(
                self,
                "Erreur de nettoyage",
                (
                    "Impossible de supprimer complètement "
                    "le projet provisoire.\n\n"
                    + str(e)
                )
            )

            event.ignore()
            return

        event.accept()

    def cleanup_abandoned_preprocessing(self):
        #
        # Libérer tous les fichiers utilisés
        # par les lecteurs.
        #
        self.playback.unload()
        self.result_playback.unload()

        #
        # Supprimer les WAV temporaires.
        #
        self.cleanup_temporary_wav_files()

        #
        # Supprimer le dossier projet provisoire
        # et tout ce qu'il contient.
        #
        if self.project_folder.exists():

            last_error = None

            for attempt in range(3):
                try:
                    shutil.rmtree(
                        self.project_folder
                    )
                    return

                except FileNotFoundError:
                    return

                except OSError as e:
                    last_error = e

                    if attempt < 2:
                        time.sleep(
                            0.15
                        )

            if last_error is not None:
                raise last_error

    def remove_file_with_retry(
        self,
        file_path,
        attempts=3,
        delay=0.15
    ):
        file_path = Path(
            file_path
        )

        if not file_path.exists():
            return True

        last_error = None

        for attempt in range(
            attempts
        ):
            try:
                file_path.unlink()
                return True

            except FileNotFoundError:
                return True

            except OSError as e:
                last_error = e

                if attempt < attempts - 1:
                    time.sleep(
                        delay
                    )

        print(
            "[CLEANUP] Impossible de supprimer : "
            f"{file_path}"
        )

        if last_error is not None:
            print(
                "[CLEANUP] "
                f"{type(last_error).__name__}: "
                f"{last_error}"
            )

        return False

    def cleanup_temporary_wav_files(self):
        temp_files = set()

        #
        # WAV temporaires de la waveform originale.
        #
        if (
            self.waveform_widget.document
            is not None
        ):
            display_wav = (
                self.waveform_widget
                .document
                .display_wav
            )

            processing_wav = (
                self.waveform_widget
                .document
                .processing_wav
            )

            if display_wav is not None:
                temp_files.add(
                    Path(display_wav)
                )

            if processing_wav is not None:
                temp_files.add(
                    Path(processing_wav)
                )

        #
        # WAV intermédiaires produits
        # par le pipeline audio.
        #
        processing_wav = Path(
            self.processing_wav
        )

        temp_files.update(
            processing_wav.parent.glob(
                f"{processing_wav.stem}*.wav"
            )
        )

        #
        # WAV de travail final situé
        # dans le dossier projet.
        #
        temp_files.add(
            self.project_folder
            / "audio_processed.wav"
        )

        #
        # WAV temporaires générés pour
        # la waveform du résultat.
        #
        if (
            self.result_waveform_widget.document
            is not None
        ):
            result_display_wav = (
                self.result_waveform_widget
                .document
                .display_wav
            )

            result_processing_wav = (
                self.result_waveform_widget
                .document
                .processing_wav
            )

            if result_display_wav is not None:
                temp_files.add(
                    Path(result_display_wav)
                )

            if result_processing_wav is not None:
                temp_files.add(
                    Path(result_processing_wav)
                )

        #
        # Le fichier final validé doit
        # impérativement être conservé.
        #
        final_file = (
            Path(self.processed_audio_file)
            if self.processed_audio_file
            else None
        )

       #
        # Suppression des WAV temporaires.
        #
        failed_files = []

        for temp_file in temp_files:

            if temp_file == final_file:
                continue

            if not self.remove_file_with_retry(
                temp_file
            ):
                failed_files.append(
                    temp_file
                )

        return failed_files