from pathlib import Path
import subprocess
import tempfile

import numpy as np

from services.resources import resource_path
from models.audio_document import AudioDocument


class AudioWaveformService:

    def __init__(self):

        self.ffmpeg = resource_path(
            "tools/ffmpeg/ffmpeg.exe"
        )

    def extract_waveform(
        self,
        audio_file
    ):

        temp_dir = (
            Path(tempfile.gettempdir())
            / "TranscriptAudio"
        )

        temp_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        temp_wav = (
            temp_dir
            / f"{Path(audio_file).stem}_working.wav"
        )  
        

        command = [

            str(self.ffmpeg),

            "-y",

            "-i",
            str(audio_file),

            "-ac",
            "1",

            "-ar",
            "1000",

            str(temp_wav)
        ]

        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        import wave

        with wave.open(
            str(temp_wav),
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
            working_wav=temp_wav,
            waveform=samples,
            duration_seconds=duration,
            sample_rate=sample_rate,
            channels=channels
        )