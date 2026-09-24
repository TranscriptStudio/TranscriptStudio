from pathlib import Path


AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".opus",
}


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".mpeg",
    ".mpg",
    ".ts",
    ".m2ts",
}


MEDIA_EXTENSIONS = (
    AUDIO_EXTENSIONS
    | VIDEO_EXTENSIONS
)


def is_audio_file(
    file_path
):
    return (
        Path(file_path)
        .suffix
        .lower()
        in AUDIO_EXTENSIONS
    )


def is_video_file(
    file_path
):
    return (
        Path(file_path)
        .suffix
        .lower()
        in VIDEO_EXTENSIONS
    )


def is_supported_media_file(
    file_path
):
    return (
        Path(file_path)
        .suffix
        .lower()
        in MEDIA_EXTENSIONS
    )


def build_media_filter():
    extensions = sorted(
        MEDIA_EXTENSIONS
    )

    patterns = " ".join(
        f"*{extension}"
        for extension in extensions
    )

    return (
        f"Médias supportés ({patterns});;"
        "Tous les fichiers (*.*)"
    )