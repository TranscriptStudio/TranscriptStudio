import atexit
import shutil
import tempfile
import uuid

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

# Creer le repertoire de donnees applicatives (cache, config, etc.)
APP_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# Dossier temporaire de l'application dans le
# systeme. Les fichiers intermediaires (waveform,
# wav de traitement) y sont regroupes.
TEMP_DIR = (
    Path(tempfile.gettempdir())
    / APP_NAME
)

# Sous-repertoire temporaire unique par session
# de travail : deux instances simultanees de
# l'application, ou deux executions successives
# traitant des medias de meme nom, ne se
# marchent plus dessus.
SESSION_TEMP_DIR = (
    TEMP_DIR
    / uuid.uuid4().hex[:12]
)


def ensure_session_temp_dir() -> Path:
    """
    Cree si necessaire le sous-repertoire
    temporaire de la session et le retourne.
    """

    SESSION_TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    return SESSION_TEMP_DIR


def cleanup_session_temp_dir():
    """
    Supprime au mieux le sous-repertoire
    temporaire de la session (appele a la
    fermeture de l'application).
    """

    shutil.rmtree(
        SESSION_TEMP_DIR,
        ignore_errors=True
    )


atexit.register(
    cleanup_session_temp_dir
)

# Note: PROJECTS_DIR n'est plus cree automatiquement ici.
# Le repertoire projets est choisi par l'utilisateur au premier lancement.
# Si un PROJECTS_DIR existe deja (installation existante), il sera utilise.
# Sinon, une suggestion sera proposee via QStandardPaths.DocumentsLocation.

# Ancien emplacement pour compatibilite avec les installations existantes
LEGACY_PROJECTS_DIR = (
    APP_DATA_DIR
    / "Projects"
)
