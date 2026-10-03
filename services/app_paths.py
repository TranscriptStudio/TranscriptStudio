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

# Note: PROJECTS_DIR n'est plus cree automatiquement ici.
# Le repertoire projets est choisi par l'utilisateur au premier lancement.
# Si un PROJECTS_DIR existe deja (installation existante), il sera utilise.
# Sinon, une suggestion sera proposee via QStandardPaths.DocumentsLocation.

# Ancien emplacement pour compatibilite avec les installations existantes
LEGACY_PROJECTS_DIR = (
    APP_DATA_DIR
    / "Projects"
)