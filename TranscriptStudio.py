# app.py

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from services.resources import resource_path
from ui.home_window import HomeWindow

app = QApplication([])
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