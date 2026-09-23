# services/audio_processing_pipeline.py

from pathlib import Path
import subprocess
from services.silence_detection_service import SilenceDetectionService
from services.ffmpeg_paths import FFMPEG_PATH


class AudioProcessingPipeline:

    def __init__(
        self,
        audio_file,
        working_wav,
        settings
    ):
        
        self.audio_file = audio_file

        self.working_wav = working_wav

        self.settings = settings

        self.working_file = working_wav

    def run(self):
        current_file = self.working_wav

        current_file = self.apply_trim(
            current_file
        )

        current_file = (
            self.apply_silence_removal(
                current_file
            )
        )

        current_file = self.apply_speed_up(
            current_file
        )

        return current_file

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

        print("[PIPELINE] Découpe")

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
        if self.settings.silence_enabled:

            print(
                "[PIPELINE] Suppression silences"
            )

            detector = (
                SilenceDetectionService()
            )

            silences = (
                detector.detect_silences(
                    audio_file,
                    self.settings.silence_threshold_db,
                    self.settings.silence_min_duration
                )
            )

            print(
                f"{len(silences)} silence(s) trouvé(s)"
            )
            
            for start, end in silences[:20]:

                print(
                    f"Silence : "
                    f"{start:.3f}s -> "
                    f"{end:.3f}s"
                )
            

        return audio_file

    def apply_speed_up(
        self,
        audio_file
    ):
        if self.settings.speed_enabled:

            print(
                "[PIPELINE] Accélération"
            )

        return audio_file