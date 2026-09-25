# services/audio_processing_pipeline.py

from pathlib import Path
import subprocess
from services.silence_detection_service import SilenceDetectionService
from services.silence_removal_service import SilenceRemovalService
from services.ffmpeg_paths import FFMPEG_PATH


class AudioProcessingPipeline:

    def __init__(
        self,
        audio_file,
        processin_wav,
        settings,
        output_file,
        progress_callback=None
    ):
        self.audio_file = audio_file
        self.processin_wav = processin_wav
        self.settings = settings
        self.output_file = Path(
            output_file
        )
        self.working_file = processin_wav
        self.progress_callback = (
            progress_callback
        )

    def report_progress(
        self,
        value,
        message
    ):
        if self.progress_callback:
            self.progress_callback(
                value,
                message
            )
            
    def run(self):

        current_file = self.processin_wav

        self.report_progress(
            5,
            "Préparation du traitement..."
        )

        self.report_progress(
            10,
            "Découpe..."
        )

        current_file = self.apply_trim(
            current_file
        )

        self.report_progress(
            30,
            "Découpe terminée"
        )

        self.report_progress(
            35,
            "Suppression des silences..."
        )

        current_file = (
            self.apply_silence_removal(
                current_file
            )
        )

        self.report_progress(
            60,
            "Suppression des silences terminée"
        )

        self.report_progress(
            65,
            "Accélération..."
        )

        current_file = self.apply_speed_up(
            current_file
        )

        self.report_progress(
            80,
            "Accélération terminée"
        )

        final_file = self.output_file

        if current_file != final_file:

            import shutil

            shutil.copy2(
                current_file,
                final_file
            )

        return final_file

    def apply_trim(
        self,
        audio_file
    ):
        if not (
            self.settings.trim_start_enabled
            or
            self.settings.trim_end_enabled
        ):
            return audio_file

        start_time = (
            self.settings.trim_start_time
            if self.settings.trim_start_enabled
            else 0.0
        )

        output_file = (
            audio_file.parent
            / f"{audio_file.stem}_trim.wav"
        )

        command = [
            str(FFMPEG_PATH),
            "-y",
            "-i",
            str(audio_file),
            "-ss",
            str(start_time),
        ]

        if self.settings.trim_end_enabled:

            duration = (
                self.settings.trim_end_time
                - start_time
            )

            command.extend([
                "-t",
                str(duration)
            ])

        command.append(
            str(output_file)
        )

        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        self.working_file = output_file

        return output_file

    def apply_silence_removal(
        self,
        audio_file
    ):
        if not self.settings.silence_enabled:
            return audio_file

        detector = (
            SilenceDetectionService()
        )

        detected_silences = (
            detector.detect_silences(
                audio_file,
                self.settings.silence_threshold_db,
                self.settings.silence_min_duration
            )
        )

        if not detected_silences:
            return audio_file

        #
        # Appliquer exactement le même buffer
        # que celui utilisé par l'analyse
        # prévisionnelle et la waveform.
        #
        buffer_duration = max(
            0.0,
            self.settings.silence_buffer_duration
        )

        removal_silences = []

        for start, end in detected_silences:
            removal_start = (
                start
                + buffer_duration
            )

            removal_end = (
                end
                - buffer_duration
            )

            #
            # Si le buffer occupe toute la zone,
            # aucune partie de ce silence
            # ne doit être supprimée.
            #
            if removal_end <= removal_start:
                continue

            removal_silences.append(
                (
                    removal_start,
                    removal_end
                )
            )


        if not removal_silences:
            return audio_file

        output_file = (
            audio_file.parent
            / f"{audio_file.stem}_nosilence.wav"
        )

        remover = (
            SilenceRemovalService()
        )

        remover.remove_silences(
            audio_file,
            removal_silences,
            output_file
        )

        self.working_file = (
            output_file
        )

        return output_file

    def apply_speed_up(
        self,
        audio_file
    ):

        if not self.settings.speed_enabled:
            return audio_file


        speed_ratio = (
            1.0
            + self.settings.speed_percent / 100.0
        )

        output_file = (
            audio_file.parent
            / f"{audio_file.stem}_speed.wav"
        )

        command = [
            str(FFMPEG_PATH),
            "-y",
            "-i",
            str(audio_file),
            "-filter:a",
            f"atempo={speed_ratio}",
            str(output_file)
        ]

        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        self.working_file = output_file

        return output_file