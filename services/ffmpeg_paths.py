from pathlib import Path

from services.resources import (
    resource_path
)


FFMPEG_PATH = resource_path(
    "tools/ffmpeg/ffmpeg.exe"
)

FFPROBE_PATH = resource_path(
    "tools/ffmpeg/ffprobe.exe"
)