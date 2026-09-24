# silence_detection_service.py

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
        )

        if samples.size == 0:
            return []

        #
        # Conversion du seuil dB en amplitude
        # dans l'échelle native int16.
        #
        amplitude_threshold = (
            32768.0
            * (
                10 ** (
                    threshold_db / 20.0
                )
            )
        )

        #
        # Conversion en int32 indispensable
        # avant abs() pour éviter le cas
        # particulier de -32768 en int16.
        #
        absolute_samples = np.abs(
            samples.astype(
                np.int32
            )
        )

        #
        # True = échantillon silencieux.
        #
        silence_mask = (
            absolute_samples
            < amplitude_threshold
        )

        #
        # Détection vectorisée des transitions :
        #
        #  1 = début d'un silence
        # -1 = fin d'un silence
        #
        transitions = np.diff(
            silence_mask.astype(
                np.int8
            )
        )

        silence_starts = (
            np.flatnonzero(
                transitions == 1
            )
            + 1
        )

        silence_ends = (
            np.flatnonzero(
                transitions == -1
            )
            + 1
        )

        #
        # Si le fichier commence directement
        # par du silence, aucune transition
        # False -> True n'existe pour ce début.
        #
        if silence_mask[0]:
            silence_starts = np.concatenate(
                (
                    np.array(
                        [0],
                        dtype=np.int64
                    ),
                    silence_starts
                )
            )

        #
        # Si le fichier se termine par du silence,
        # aucune transition True -> False n'existe.
        #
        if silence_mask[-1]:
            silence_ends = np.concatenate(
                (
                    silence_ends,
                    np.array(
                        [silence_mask.size],
                        dtype=np.int64
                    )
                )
            )

        #
        # Durée minimale exprimée directement
        # en nombre d'échantillons.
        #
        min_samples = (
            min_duration_seconds
            * sample_rate
        )

        silence_lengths = (
            silence_ends
            - silence_starts
        )

        valid_silences = (
            silence_lengths
            >= min_samples
        )

        silence_starts = silence_starts[
            valid_silences
        ]

        silence_ends = silence_ends[
            valid_silences
        ]

        #
        # Conversion finale des positions
        # d'échantillons vers les secondes.
        #
        return [
            (
                start / sample_rate,
                end / sample_rate
            )
            for start, end in zip(
                silence_starts,
                silence_ends
            )
        ]