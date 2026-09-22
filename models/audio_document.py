# models/audio_document.py
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class AudioDocument:

    original_file: Path

    working_wav: Path | None = None

    duration_seconds: float = 0.0

    waveform: np.ndarray | None = None

    sample_rate: int = 0

    channels: int = 0

    zoom_factor: float = 1.0

    view_offset: float = 0.0

    current_time: float = 0.0

    @property
    def duration_text(self):

        total = int(
            self.duration_seconds
        )

        hours = total // 3600

        minutes = (
            total % 3600
        ) // 60

        seconds = total % 60

        if hours > 0:

            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{seconds:02d}"
            )

        return (
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )