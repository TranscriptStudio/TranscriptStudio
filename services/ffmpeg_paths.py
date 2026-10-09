import sys
from pathlib import Path
import shutil

from services.resources import resource_path
from services.settings import SettingsManager


# P8 : Organisation multiplateforme des binaires FFmpeg
# Structure cible : tools/ffmpeg/{platform}/ffmpeg
FFMPEG_DIR = resource_path(
    Path(
        "tools"
    )
    / "ffmpeg"
)

# Nom de l'executable FFmpeg selon la plateforme
FFMPEG_NAME = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"

# Pour la compatibilité descendante, on garde aussi le chemin plat
FFMPEG_PATH = FFMPEG_DIR / FFMPEG_NAME

# P8 : Noms des sous-dossiers par plateforme
PLATFORM_DIRS = {
    "win32": "windows",
    "darwin": "macos",
    "linux": "linux",
    "linux2": "linux",
}

# P8 : Chemins des binaires embarqués par plateforme
def _get_embedded_ffmpeg_paths():
    """
    Retourne les chemins possibles pour les binaires FFmpeg embarqués
    selon la plateforme.
    """
    platform = sys.platform
    platform_dir = PLATFORM_DIRS.get(platform, "linux")
    
    # Chemins à essayer (ancien format plat et nouveau format par plateforme)
    paths = [
        # Nouveau format : tools/ffmpeg/{platform}/ffmpeg
        FFMPEG_DIR / platform_dir / FFMPEG_NAME,
        # Ancien format plat : tools/ffmpeg/ffmpeg(.exe)
        FFMPEG_DIR / FFMPEG_NAME,
    ]
    
    return paths


# FFPROBE_NAME = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
# FFPROBE_PATH = FFMPEG_DIR / FFPROBE_NAME


def get_ffmpeg_path(settings=None):
    """
    P8 : Résolveur FFmpeg avec stratégie hiérarchique.
    
    Stratégie de résolution :
    1. Binaire embarqué dans tools/ffmpeg/{platform}/ffmpeg
    2. Configuration utilisateur (via paramètres)
    3. PATH système
    
    Args:
        settings: Instance de SettingsManager (optionnel) pour la configuration utilisateur
        
    Returns:
        Path: Chemin absolu vers ffmpeg.exe/ffmpeg, ou juste le nom si non trouvé
    """
    # 1. Essayer les chemins embarqués (nouveau format et ancien format)
    for embedded_path in _get_embedded_ffmpeg_paths():
        if embedded_path.is_file():
            return embedded_path
    
    # 2. Essayer la configuration utilisateur
    if settings is None:
        settings = SettingsManager()
    
    custom_ffmpeg = settings.get_ffmpeg_path() if hasattr(settings, 'get_ffmpeg_path') else None
    if custom_ffmpeg:
        custom_path = Path(custom_ffmpeg)
        if custom_path.is_file():
            return custom_path
    
    # 3. Essayer PATH système
    if shutil.which(FFMPEG_NAME):
        return Path(shutil.which(FFMPEG_NAME))
    
    # Retourne juste le nom pour que le système recherche dans PATH
    return Path(FFMPEG_NAME)


def validate_ffmpeg_tools():
    """
    P8 : Vérifie que les exécutables FFmpeg nécessaires
    à Transcript Studio sont disponibles avec stratégie hiérarchique.

    Stratégie :
    1. Vérifie d'abord dans tools/ffmpeg/{platform}/ ou tools/ffmpeg/
    2. Sinon, vérifie la configuration utilisateur
    3. Sinon, vérifie la disponibilité dans PATH
    4. Retourne un message clair si introuvable

    Retourne :
        (True, None)
        si tout est disponible.

        (False, message)
        lorsqu'un fichier est absent.
    """
    # 1. Essayer les chemins embarqués
    for embedded_path in _get_embedded_ffmpeg_paths():
        if embedded_path.is_file():
            return (True, None)
    
    # 2. Essayer PATH système
    if shutil.which(FFMPEG_NAME):
        return (True, None)

    # 3. Message d'erreur clair
    return (
        False,
        (
            "FFmpeg n'est pas disponible.\n\n"
            f"Transcript Studio a besoin de FFmpeg ({FFMPEG_NAME}) pour fonctionner.\n\n"
            "Stratégie de résolution :\n"
            "1. Binaire embarqué : placez ffmpeg.exe/ffmpeg dans tools/ffmpeg/{platform}/ ou tools/ffmpeg/\n"
            "2. Configuration utilisateur : configurez le chemin dans les paramètres\n"
            "3. PATH système : installez FFmpeg et assurez-vous qu'il est dans votre PATH\n\n"
            "Installation recommandée :\n"
            "- Windows : Copiez ffmpeg.exe dans tools/ffmpeg/windows/\n"
            "- macOS : Installez via Homebrew ou copiez ffmpeg dans tools/ffmpeg/macos/\n"
            "- Linux : Installez via apt/yum/dnf ou copiez ffmpeg dans tools/ffmpeg/linux/\n\n"
            "Une fois installé, veuillez redémarrer l'application."
        )
    )


def find_ffmpeg_path():
    """
    P8 : Fonction de compatibilité pour trouver le chemin FFmpeg.
    Utilise get_ffmpeg_path() avec un SettingsManager par défaut.
    
    Returns:
        Path: Chemin vers l'executable FFmpeg
    """
    return get_ffmpeg_path()
