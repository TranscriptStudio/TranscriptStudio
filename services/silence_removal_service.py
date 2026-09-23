# services/silence_removal_service.py

import wave
import numpy as np


class SilenceRemovalService:

    def remove_silences(
        self,
        wav_file,
        silences,
        output_file
    ):

        with wave.open(
            str(wav_file),
            "rb"
        ) as wav:

            params = wav.getparams()

            frame_count = wav.getnframes()

            sample_rate = wav.getframerate()

            frames = wav.readframes(
                frame_count
            )

        samples = np.frombuffer(
            frames,
            dtype=np.int16
        )

        keep_segments = []

        last_end = 0

        for start_time, end_time in silences:

            start_sample = int(
                start_time * sample_rate
            )

            end_sample = int(
                end_time * sample_rate
            )

            if start_sample > last_end:

                keep_segments.append(
                    samples[
                        last_end:start_sample
                    ]
                )

            last_end = end_sample

        if last_end < len(samples):

            keep_segments.append(
                samples[last_end:]
            )

        if keep_segments:

            result = np.concatenate(
                keep_segments
            )

        else:

            result = np.array(
                [],
                dtype=np.int16
            )

        with wave.open(
            str(output_file),
            "wb"
        ) as wav:

            wav.setparams(params)

            wav.writeframes(
                result.tobytes()
            )

        return output_file