from pathlib import Path
import sys


def resource_path(relative_path: Path) -> Path:
    """
    Compatible Python normal et PyInstaller.
    """

    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent

    return base_path / relative_path