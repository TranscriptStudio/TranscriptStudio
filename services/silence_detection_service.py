import wave

import numpy as np


class SilenceDetectionService:

    def detect_silences(
        self,
        wav_file,
        threshold_db,
        min_duration_seconds
    ):

        with wave.open(
            str(wav_file),
            "rb"
        ) as wav:

            sample_rate = wav.getframerate()

            frame_count = wav.getnframes()

            frames = wav.readframes(
                frame_count
            )

        samples = np.frombuffer(
            frames,
            dtype=np.int16
        ).astype(
            np.float32
        )

        samples = samples / 32768.0

        amplitude_threshold = (
            10 ** (
                threshold_db / 20
            )
        )

        silence_mask = (
            np.abs(samples)
            < amplitude_threshold
        )

        silences = []

        start_index = None

        for i, is_silent in enumerate(
            silence_mask
        ):

            if is_silent:

                if start_index is None:
                    start_index = i

            else:

                if start_index is None:
                    continue

                duration = (
                    i - start_index
                ) / sample_rate

                if (
                    duration
                    >= min_duration_seconds
                ):

                    silences.append(
                        (
                            start_index
                            / sample_rate,

                            i
                            / sample_rate
                        )
                    )

                start_index = None

        return silences