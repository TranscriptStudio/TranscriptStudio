# app.py

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from services.resources import resource_path
from ui.home_window import HomeWindow
from ui.settings_dialog import SettingsDialog
from services.settings import SettingsManager
from services.theme_manager import ThemeManager
from services.diagnostics import install_excepthook
from services.diagnostics import install_qt_message_handler

install_excepthook()
install_qt_message_handler()

# Capturer les crashs natifs (SIGABRT, acces memoire
# invalides) avec la pile Python de tous les threads
# au moment du crash : sans console, ils seraient
# sinon totalement silencieux pour le support.
import faulthandler

from services.app_paths import APP_DATA_DIR

_FAULTHANDLER_LOG = open(
    APP_DATA_DIR / "faulthandler.log",
    "a",
    encoding="utf-8",
)
faulthandler.enable(
    file=_FAULTHANDLER_LOG,
    all_threads=True,
)

app = QApplication([])

settings = SettingsManager()

ThemeManager.apply_theme(
    app,
    settings.get_theme()
)

# Charger les feuilles de style des deux themes
# maintenant, dans un contexte de demarrage calme.
# En binaire compile, l'import paresseux des
# ressources qdarktheme au moment du changement
# de theme fait crasher l'application.
ThemeManager.preload_style_sheets()
# Icone de l'application : icon.ico pour Windows,
# repli sur logo.png (lisible sur tous les OS),
# demarrage sans icone si aucun des deux.
app_icon_path = resource_path("icons/icon.ico")

if not app_icon_path.is_file():
    app_icon_path = resource_path("icons/logo.png")

if app_icon_path.is_file():
    app.setWindowIcon(
        QIcon(
            str(app_icon_path)
        )
    )

# Verifier si la configuration initiale est terminee
if not settings.is_initial_setup_completed():
    # Mode first-run : ouvrir les parametres pour configuration obligatoire
    # Le titre et le bouton Quitter sont geres automatiquement dans SettingsDialog
    settings_dialog = SettingsDialog(first_run=True)
    
    # Executer le dialogue - il doit etre modal et bloquant
    result = settings_dialog.exec()
    
    if not result:
        # L'utilisateur a clique sur Quitter ou ferme la fenetre -> quitter l'application
        app.quit()
        exit(0)
    
    # Recharger les parametres pour s'assurer qu'ils sont a jour
    settings.load()
    
    # Verifier que la configuration a ete validee correctement
    if not settings.is_initial_setup_completed():
        # Si on arrive ici, c'est qu'il y a eu un probleme
        app.quit()
        exit(1)

# Configuration terminee, on peut lancer l'application normale
window = HomeWindow()

window.show()

app.exec()