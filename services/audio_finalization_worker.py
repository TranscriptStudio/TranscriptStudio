# audio_finalization_worker.py

import subprocess
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
)

from services.ffmpeg_paths import (
    FFMPEG_PATH
)


class AudioFinalizationWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        source_wav,
        original_file,
        project_folder
    ):
        super().__init__()

        self.source_wav = Path(
            source_wav
        )

        self.original_file = Path(
            original_file
        )

        self.project_folder = Path(
            project_folder
        )

    @Slot()
    def run(self):
        try:
            if not self.source_wav.exists():
                raise FileNotFoundError(
                    "Le fichier audio traité "
                    "est introuvable : "
                    f"{self.source_wav}"
                )

            final_extension = (
                self.original_file
                .suffix
                .lower()
            )

            if not final_extension:
                raise ValueError(
                    "Impossible de déterminer "
                    "l'extension du fichier original."
                )

            final_file = (
                self.project_folder
                / (
                    f"{self.original_file.stem}"
                    f"_timeoptimized"
                    f"{final_extension}"
                )
            )

            command = [
                str(FFMPEG_PATH),
                "-y",
                "-i",
                str(self.source_wav),
                str(final_file),
            ]

            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )

            if not final_file.exists():
                raise RuntimeError(
                    "Le fichier audio final "
                    "n'a pas été créé."
                )

            self.finished.emit(
                final_file
            )

        except Exception as e:
            self.error.emit(
                str(e)
            )
