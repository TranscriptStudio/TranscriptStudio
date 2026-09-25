from pathlib import Path

from services.resources import resource_path


FFMPEG_DIR = resource_path(
    Path(
        "tools"
    )
    / "ffmpeg"
)


FFMPEG_PATH = (
    FFMPEG_DIR
    / "ffmpeg.exe"
)


# FFPROBE_PATH = (
#     FFMPEG_DIR
#     / "ffprobe.exe"
# )


def validate_ffmpeg_tools():
    """
    Vérifie que les exécutables FFmpeg nécessaires
    à Transcript Studio sont disponibles.

    Retourne :
        (True, None)
        si tout est disponible.

        (False, message)
        lorsqu'un fichier est absent.
    """

    missing_files = []

    if not FFMPEG_PATH.is_file():
        missing_files.append(
            FFMPEG_PATH
        )

    # if not FFPROBE_PATH.is_file():
    #     missing_files.append(
    #         FFPROBE_PATH
    #     )

    if not missing_files:
        return (
            True,
            None
        )

    missing_text = "\n".join(
        str(path)
        for path in missing_files
    )

    return (
        False,
        (
            "Les outils FFmpeg nécessaires "
            "à Transcript Studio sont introuvables.\n\n"
            "Fichier(s) manquant(s) :\n"
            f"{missing_text}"
        )
    )