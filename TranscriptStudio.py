# app.py

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from services.resources import resource_path
from ui.home_window import HomeWindow
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

window = HomeWindow()

window.show()

app.exec()