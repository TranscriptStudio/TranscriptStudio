# services/subprocess_flags.py

import subprocess
import sys


# P11.1 : en application compilee sans console
# (--windows-console-mode=disable), chaque sous-processus
# console (ffmpeg.exe) ouvre sa propre fenetre console
# Windows qui flashe a l'ecran. CREATE_NO_WINDOW
# supprime cette fenetre. Sans effet sur macOS/Linux.
CREATE_NO_WINDOW = (
    subprocess.CREATE_NO_WINDOW
    if sys.platform == "win32"
    else 0
)
