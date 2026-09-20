from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
)

from services.elevenlabs_api import (
    ElevenLabsAPI
)


class ElevenLabsAccountDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            "Compte ElevenLabs"
        )

        self.resize(
            500,
            350
        )

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        try:

            info = (
                ElevenLabsAPI()
                .get_account_summary()
            )
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
                info[
                    "reset_date"
                ].strftime(
                    "%d/%m/%Y"
                )
            )
        ]

        for label, value in fields:

            layout.addWidget(
                QLabel(
                    f"<b>{label}</b> : {value}"
                )
            )
        layout.addWidget(
            QLabel(
                "<b>Taux d'utilisation des crédits</b>"
            )
        )
        progress = QProgressBar()

        progress.setRange(
            0,
            100
        )

        progress.setValue(
            usage_percent)
        
        progress.setStyleSheet("""
        QProgressBar {
            border: 1px solid #D0D0D0;
            border-radius: 8px;
            text-align: center;
            height: 22px;
        }

        QProgressBar::chunk {
            background-color: #4A90E2;
            border-radius: 8px;
        }
        """)
        layout.addWidget(
            progress
        )
        layout.addWidget(
            QLabel(
                f"{str(info['used'])} / {str(info['limit'])} crédits"
            )
        )
        if usage_percent < 60:
            color = "#4A90E2"

        elif usage_percent < 85:
            color = "#F5A623"

        else:
            color = "#D0021B"
        progress.setStyleSheet(f"""
        QProgressBar {{
            border: 1px solid #D0D0D0;
            border-radius: 8px;
            text-align: center;
            height: 22px;
        }}

        QProgressBar::chunk {{
            background-color: {color};
            border-radius: 8px;
        }}
        """)
