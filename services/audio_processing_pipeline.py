# services/audio_processing_pipeline.py

from pathlib import Path
from services.silence_detection_service import SilenceDetectionService

class AudioProcessingPipeline:

    def __init__(
        self,
        audio_file,
        settings
    ):
        self.audio_file = audio_file
        self.settings = settings

        self.working_file = self.audio_file

    def run(self):
        current_file = self.audio_file

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
        if (
            self.settings.trim_start_enabled
            or
            self.settings.trim_end_enabled
        ):
            print(
                "[PIPELINE] Découpe"
            )

        return audio_file

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

            # silences = (
            #     detector.detect_silences(
            #         audio_file,
            #         self.settings.silence_threshold_db,
            #         self.settings.silence_min_duration
            #     )
            # )

            # print(
            #     f"{len(silences)} silence(s) trouvé(s)"
            # )
            


            # for start, end in silences[:20]:

            #     print(
            #         f"Silence : "
            #         f"{start:.3f}s -> "
            #         f"{end:.3f}s"
            #     )
            print("TODO : utiliser working_wav")

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