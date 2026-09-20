from pathlib import Path
from platformdirs import user_data_dir


APP_NAME = "TranscriptStudio"
APP_AUTHOR = "DFrechet"

APP_DATA_DIR = Path(
    user_data_dir(
        APP_NAME,
        APP_AUTHOR
    )
)

APP_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

PROJECTS_DIR = (
    APP_DATA_DIR
    / "Projects"
)

PROJECTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)