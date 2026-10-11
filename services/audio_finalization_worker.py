# audio_finalization_worker.py

import subprocess
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
)

from services.ffmpeg_paths import get_ffmpeg_path
from services.subprocess_flags import CREATE_NO_WINDOW
from services.media_formats import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS



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

    def get_final_extension(self):
        original_extension = (
            self.original_file
            .suffix
            .lower()
        )

        if original_extension in AUDIO_EXTENSIONS:
            return original_extension

        if original_extension in VIDEO_EXTENSIONS:
            return ".m4a"

        raise ValueError(
            "Format du fichier original "
            "non pris en charge pour la "
            "finalisation : "
            f"{original_extension or '(aucune extension)'}"
        )

    def build_ffmpeg_command(
        self,
        final_file,
        final_extension
    ):
        command = [
            str(get_ffmpeg_path()),
            "-y",
            "-i",
            str(self.source_wav),
            "-vn",
        ]

        if final_extension == ".wav":
            command.extend([
                "-c:a",
                "pcm_s16le",
            ])

        elif final_extension == ".mp3":
            command.extend([
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
            ])

        elif final_extension in {
            ".m4a",
            ".aac",
        }:
            command.extend([
                "-c:a",
                "aac",
                "-b:a",
                "192k",
            ])

        elif final_extension == ".flac":
            command.extend([
                "-c:a",
                "flac",
            ])

        elif final_extension == ".ogg":
            command.extend([
                "-c:a",
                "libvorbis",
                "-q:a",
                "5",
            ])

        elif final_extension == ".opus":
            command.extend([
                "-c:a",
                "libopus",
                "-b:a",
                "128k",
            ])

        else:
            raise ValueError(
                "Aucun encodeur configuré "
                "pour le format final : "
                f"{final_extension}"
            )

        command.append(
            str(final_file)
        )

        return command

    @Slot()
    def run(self):
        try:
            if not self.source_wav.exists():
                raise FileNotFoundError(
                    "Le fichier audio traité "
                    "est introuvable : "
                    f"{self.source_wav}"
                )

            if not self.original_file.exists():
                raise FileNotFoundError(
                    "Le fichier original "
                    "est introuvable : "
                    f"{self.original_file}"
                )

            final_extension = (
                self.get_final_extension()
            )

            final_file = (
                self.project_folder
                / (
                    f"{self.original_file.stem}"
                    f"_timeoptimized"
                    f"{final_extension}"
                )
            )

            command = (
                self.build_ffmpeg_command(
                    final_file,
                    final_extension
                )
            )

            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=CREATE_NO_WINDOW,
            )

            if result.returncode != 0:
                error_message = (
                    result.stderr.strip()
                )

                if not error_message:
                    error_message = (
                        "FFmpeg a retourné une erreur "
                        "sans message détaillé."
                    )

                raise RuntimeError(
                    "La conversion finale a échoué.\n\n"
                    f"{error_message}"
                )

            if not final_file.exists():
                raise RuntimeError(
                    "FFmpeg n'a signalé aucune erreur, "
                    "mais le fichier audio final "
                    "n'a pas été créé."
                )

            if final_file.stat().st_size == 0:
                raise RuntimeError(
                    "Le fichier audio final créé "
                    "est vide."
                )

            self.finished.emit(
                final_file
            )

        except Exception as e:
            self.error.emit(
                str(e)
            )