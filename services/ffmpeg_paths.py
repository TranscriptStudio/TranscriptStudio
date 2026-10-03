import sys
from pathlib import Path

from services.resources import resource_path


FFMPEG_DIR = resource_path(
    Path(
        "tools"
    )
    / "ffmpeg"
)

# Nom de l'executable FFmpeg selon la plateforme
FFMPEG_NAME = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"

# Chemin vers l'executable FFmpeg dans le dossier tools
FFMPEG_PATH = FFMPEG_DIR / FFMPEG_NAME


# FFPROBE_NAME = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
# FFPROBE_PATH = FFMPEG_DIR / FFPROBE_NAME


def get_ffmpeg_path():
    """
    Retourne le chemin vers l'executable FFmpeg.
    
    Stratégie de résolution :
    1. Vérifie d'abord dans le dossier tools/ffmpeg du projet
    2. Si non trouvé, retourne le nom de l'executable pour recherche dans PATH
    
    Returns:
        Path: Chemin absolu vers ffmpeg.exe/ffmpeg, ou juste le nom si non trouvé localement
    """
    if FFMPEG_PATH.is_file():
        return FFMPEG_PATH
    
    # Retourne juste le nom pour que le système recherche dans PATH
    return Path(FFMPEG_NAME)


def validate_ffmpeg_tools():
    """
    Vérifie que les exécutables FFmpeg nécessaires
    à Transcript Studio sont disponibles.

    Stratégie :
    1. Vérifie d'abord dans tools/ffmpeg/
    2. Sinon, vérifie la disponibilité dans PATH
    3. Retourne un message clair si introuvable

    Retourne :
        (True, None)
        si tout est disponible.

        (False, message)
        lorsqu'un fichier est absent.
    """

    # Vérification dans le dossier tools
    if FFMPEG_PATH.is_file():
        return (True, None)

    # Vérification dans PATH
    import shutil
    if shutil.which(FFMPEG_NAME):
        return (True, None)

    return (
        False,
        (
            "FFmpeg n'est pas disponible.\n\n"
            f"Transcript Studio a besoin de FFmpeg ({FFMPEG_NAME}) pour fonctionner.\n\n"
            "Installation recommandée :\n"
            "1. Windows : FFmpeg devrait être dans tools/ffmpeg/ffmpeg.exe\n"
            "2. macOS/Linux : Installez FFmpeg via votre gestionnaire de paquets,\n"
            "   ou placez l'executable dans tools/ffmpeg/ffmpeg\n\n"
            "Une fois installé, veuillez redémarrer l'application."
        )
    )
