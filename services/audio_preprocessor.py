from pathlib import Path


class AudioPreprocessor:

    def __init__(self):
        pass

    def estimate_duration(
        self,
        original_duration,
        settings
    ):

        duration = original_duration

        #
        # estimation naïve
        #
        if settings.speed_enabled:

            duration /= (
                1 + settings.speed_percent / 100
            )

        return duration