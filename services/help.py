from pathlib import Path
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from services.resources import (
    resource_path
)



def open_user_manual():

    pdf_path = resource_path(
    "docs/Manuel utilisateur.pdf"
)

    if pdf_path.exists():

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(pdf_path)
            )
        )