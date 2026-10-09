from pathlib import Path
import subprocess
import tempfile

import numpy as np

from services.ffmpeg_paths import (
    FFMPEG_PATH,
)
from models.audio_document import AudioDocument


class AudioWaveformService:

    def __init__(self):

        self.ffmpeg = FFMPEG_PATH

    def extract_waveform(
        self,
        audio_file
    ):

        temp_dir = (
            Path(tempfile.gettempdir())
            / "TranscriptStudio"
        )

        temp_dir.mkdir(
            parents=True,
            exist_ok=True
        )
        display_wav = (
            temp_dir
            / f"{Path(audio_file).stem}_display.wav"
        )

        processing_wav = (
            temp_dir
            / f"{Path(audio_file).stem}_processing.wav"
        )

        # temp_wav = (
        #     temp_dir
        #     / f"{Path(audio_file).stem}_working.wav"
        # )  
        

        display_command = [
            str(self.ffmpeg),
            "-y",
            "-i",
            str(audio_file),
            "-ac",
            "1",
            "-ar",
            "1000",
            str(display_wav)
        ]

        subprocess.run(
            display_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        processing_command = [
            str(self.ffmpeg),
            "-y",
            "-i",
            str(audio_file),
            "-ac",
            "1",
            "-ar",
            "44100",
            str(processing_wav)
        ]

        subprocess.run(
            processing_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        import wave

        with wave.open(
            str(display_wav),
            "rb"
        ) as wav:

            frame_count = wav.getnframes()
            sample_rate = wav.getframerate()
            channels = wav.getnchannels()

            frames = wav.readframes(
                frame_count
            )
            
            samples = np.frombuffer(
                frames,
                dtype=np.int16
            )

        # #
        # # Décimation pour affichage rapide
        # #
        # step = max(
        #     1,
        #     len(samples) // 50000
        # )

        # samples = samples[::step]

        samples = (
            samples.astype(float)
            / np.max(
                np.abs(samples)
            )
        )

        duration = frame_count / sample_rate

        return AudioDocument(
            original_file=Path(audio_file),
            display_wav=display_wav,
            processing_wav=processing_wav,  
            waveform=samples,
            duration_seconds=duration,
            sample_rate=sample_rate,
            channels=channels
        )