# elevenlabs_account_dialog.py

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
)

from services.elevenlabs_api import ElevenLabsAPI
from services.api_capabilities import has_api_key, can_access_account_info


class ElevenLabsAccountDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Compte ElevenLabs")
        self.resize(500, 350)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        if not can_access_account_info():
            QMessageBox.information(
                self,
                "Service non configuré",
                "Pour consulter les informations de votre compte ElevenLabs, "
                "vous devez d'abord configurer une clé API valide dans les paramètres."
            )
            self.close()
            return
        
        try:
            info = ElevenLabsAPI().get_account_summary()
            usage_percent = int(info["utilization"])

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                str(e)
            )
            return

        fields = [
            ("Nom", info["name"]),
            ("Plan", info["tier"]),
            ("Statut", info["status"]),
            (
                "Crédits restants",
                f"{info['remaining']:,}"
            ),
            (
                "Crédits utilisés",
                str(info["used"])
            ),
            (
                "Réinitialisation crédits",
                info["reset_date"].strftime("%d/%m/%Y")
            )
        ]

        for label, value in fields:
            layout.addWidget(
                QLabel(f"<b>{label}</b> : {value}")
            )

        layout.addWidget(
            QLabel("<b>Taux d'utilisation des crédits</b>")
        )

        progress = QProgressBar()

        progress.setRange(0, 100)
        progress.setValue(usage_percent)

        # Couleur selon le taux d'utilisation
        if usage_percent < 60:
            color = "#4A90E2"
        elif usage_percent < 85:
            color = "#F5A623"
        else:
            color = "#D0021B"

        progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #AAAAAA;
                border-radius: 8px;
                background-color: #2B2B2B;
                text-align: center;
                color: white;
                min-height: 26px;
                max-height: 26px;
            }}

            QProgressBar::chunk {{
                background-color: {color};
                border-top-left-radius: 7px;
                border-bottom-left-radius: 7px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
        """)

        layout.addWidget(progress)

        layout.addWidget(
            QLabel(
                f"{info['used']} / {info['limit']} crédits"
            )
        )