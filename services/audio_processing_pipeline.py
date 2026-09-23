# services/audio_processing_pipeline.py

from pathlib import Path

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