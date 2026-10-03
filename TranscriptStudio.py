# app.py

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from services.resources import resource_path
from ui.home_window import HomeWindow
from ui.settings_dialog import SettingsDialog
from services.settings import SettingsManager
from services.theme_manager import ThemeManager

app = QApplication([])

settings = SettingsManager()

ThemeManager.apply_theme(
    app,
    settings.get_theme()
)
app.setWindowIcon(
    QIcon(
        str(resource_path(
            "icons/icon.ico"
        ))
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