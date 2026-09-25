from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QPalette,
)


class ThemeManager:
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"

    @staticmethod
    def apply_theme(
        app,
        theme
    ):
        if theme == ThemeManager.DARK:
            ThemeManager.apply_dark(
                app
            )
            return

        if theme == ThemeManager.LIGHT:
            ThemeManager.apply_light(
                app
            )
            return

        #
        # Mode système :
        # utiliser le thème clair / sombre
        # signalé par le système à Qt.
        #
        ThemeManager.apply_system(
            app
        )

    @staticmethod
    def apply_system(
        app
    ):
        color_scheme = (
            app.styleHints()
            .colorScheme()
        )

        if (
            color_scheme
            == Qt.ColorScheme.Dark
        ):
            ThemeManager.apply_dark(
                app
            )
        else:
            ThemeManager.apply_light(
                app
            )

    @staticmethod
    def apply_dark(app):
        app.setStyle("Windows11")
        palette = QPalette()

        palette.setColor(
            QPalette.ColorRole.Window,
            QColor(45, 45, 45)
        )
        palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor(240, 240, 240)
        )
        palette.setColor(
            QPalette.ColorRole.Base,
            QColor(30, 30, 30)
        )
        palette.setColor(
            QPalette.ColorRole.AlternateBase,
            QColor(45, 45, 45)
        )
        palette.setColor(
            QPalette.ColorRole.ToolTipBase,
            QColor(240, 240, 240)
        )
        palette.setColor(
            QPalette.ColorRole.ToolTipText,
            QColor(20, 20, 20)
        )
        palette.setColor(
            QPalette.ColorRole.Text,
            QColor(240, 240, 240)
        )
        palette.setColor(
            QPalette.ColorRole.Button,
            QColor(55, 55, 55)
        )
        palette.setColor(
            QPalette.ColorRole.ButtonText,
            QColor(240, 240, 240)
        )
        palette.setColor(
            QPalette.ColorRole.BrightText,
            QColor(255, 255, 255)
        )
        palette.setColor(
            QPalette.ColorRole.Highlight,
            QColor(42, 125, 220)
        )
        palette.setColor(
            QPalette.ColorRole.HighlightedText,
            QColor(255, 255, 255)
        )
        palette.setColor(
            QPalette.ColorRole.Mid,
            QColor(95, 95, 95)
        )

        app.setPalette(
            palette
        )
        app.setStyleSheet("""
            QPushButton {
                color: palette(button-text);
                background-color: palette(button);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 4px 8px;
            }

            QPushButton:hover {
                background-color: rgb(70, 70, 70);
            }

            QPushButton:pressed {
                background-color: rgb(85, 85, 85);
            }

            QPushButton:disabled {
                color: rgb(130, 130, 130);
                background-color: rgb(50, 50, 50);
            }
        """)

    @staticmethod
    def apply_light(app):
        #
        # Utiliser le style Qt Fusion lorsque
        # le thème clair est forcé.
        #
        # Le style natif Windows peut continuer
        # à tenir compte du mode sombre de Windows
        # malgré l'application d'une QPalette claire.
        #
        app.setStyle("Windows11")

        palette = QPalette()

        #
        # Fenêtres et panneaux
        #
        palette.setColor(
            QPalette.ColorRole.Window,
            QColor(245, 245, 245)
        )
        palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor(25, 25, 25)
        )

        #
        # Zones de saisie / listes
        #
        palette.setColor(
            QPalette.ColorRole.Base,
            QColor(255, 255, 255)
        )
        palette.setColor(
            QPalette.ColorRole.AlternateBase,
            QColor(245, 245, 245)
        )
        palette.setColor(
            QPalette.ColorRole.Text,
            QColor(25, 25, 25)
        )

        #
        # Boutons
        #
        palette.setColor(
            QPalette.ColorRole.Button,
            QColor(240, 240, 240)
        )
        palette.setColor(
            QPalette.ColorRole.ButtonText,
            QColor(25, 25, 25)
        )

        #
        # Texte secondaire / séparateurs
        #
        palette.setColor(
            QPalette.ColorRole.Mid,
            QColor(150, 150, 150)
        )
        palette.setColor(
            QPalette.ColorRole.Midlight,
            QColor(205, 205, 205)
        )
        palette.setColor(
            QPalette.ColorRole.Light,
            QColor(255, 255, 255)
        )
        palette.setColor(
            QPalette.ColorRole.Dark,
            QColor(110, 110, 110)
        )
        palette.setColor(
            QPalette.ColorRole.Shadow,
            QColor(70, 70, 70)
        )

        #
        # Sélection
        #
        palette.setColor(
            QPalette.ColorRole.Highlight,
            QColor(42, 125, 220)
        )
        palette.setColor(
            QPalette.ColorRole.HighlightedText,
            QColor(255, 255, 255)
        )

        #
        # Liens
        #
        palette.setColor(
            QPalette.ColorRole.Link,
            QColor(42, 125, 220)
        )
        palette.setColor(
            QPalette.ColorRole.LinkVisited,
            QColor(90, 70, 160)
        )

        #
        # Tooltips
        #
        palette.setColor(
            QPalette.ColorRole.ToolTipBase,
            QColor(255, 255, 220)
        )
        palette.setColor(
            QPalette.ColorRole.ToolTipText,
            QColor(25, 25, 25)
        )

        #
        # Texte très contrasté
        #
        palette.setColor(
            QPalette.ColorRole.BrightText,
            QColor(255, 255, 255)
        )
        #
        # Champs de saisie et listes déroulantes.
        #
        for group in (
            QPalette.ColorGroup.Active,
            QPalette.ColorGroup.Inactive,
        ):
            palette.setColor(
                group,
                QPalette.ColorRole.Base,
                QColor(255, 255, 255)
            )
            palette.setColor(
                group,
                QPalette.ColorRole.Text,
                QColor(25, 25, 25)
            )
            palette.setColor(
                group,
                QPalette.ColorRole.Button,
                QColor(245, 245, 245)
            )
            palette.setColor(
                group,
                QPalette.ColorRole.ButtonText,
                QColor(25, 25, 25)
            )
            palette.setColor(
                group,
                QPalette.ColorRole.PlaceholderText,
                QColor(120, 120, 120)
            )
        #
        # Contrôles désactivés.
        #
        # Important : on force explicitement ces rôles
        # pour éviter le texte blanc provenant du thème
        # sombre de Windows.
        #
        disabled = QPalette.ColorGroup.Disabled

        palette.setColor(
            disabled,
            QPalette.ColorRole.WindowText,
            QColor(125, 125, 125)
        )
        palette.setColor(
            disabled,
            QPalette.ColorRole.Text,
            QColor(125, 125, 125)
        )
        palette.setColor(
            disabled,
            QPalette.ColorRole.ButtonText,
            QColor(125, 125, 125)
        )
        palette.setColor(
            disabled,
            QPalette.ColorRole.Base,
            QColor(242, 242, 242)
        )
        palette.setColor(
            disabled,
            QPalette.ColorRole.Button,
            QColor(235, 235, 235)
        )
        palette.setColor(
            disabled,
            QPalette.ColorRole.Window,
            QColor(245, 245, 245)
        )
        palette.setColor(
            disabled,
            QPalette.ColorRole.Highlight,
            QColor(190, 205, 220)
        )
        palette.setColor(
            disabled,
            QPalette.ColorRole.HighlightedText,
            QColor(110, 110, 110)
        )


        app.setPalette(
            palette
        )

        app.setStyleSheet("""
            QPushButton {
                color: palette(button-text);
                background-color: palette(button);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 4px 8px;
            }

            QPushButton:hover {
                background-color: rgb(225, 225, 225);
            }

            QPushButton:pressed {
                background-color: rgb(210, 210, 210);
            }

            QPushButton:disabled {
                color: rgb(130, 130, 130);
                background-color: rgb(235, 235, 235);
            }

            QComboBox {
                color: palette(text);
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 6px;
                padding: 5px 30px 5px 8px;
                min-height: 22px;
            }

            QComboBox:hover {
                border: 1px solid rgb(120, 120, 120);
            }

            QComboBox:focus {
                border: 1px solid rgb(42, 125, 220);
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border: none;
                background: transparent;
            }

            QComboBox QAbstractItemView {
                color: palette(text);
                background-color: palette(base);
                selection-color: palette(highlighted-text);
                selection-background-color: palette(highlight);
                border: 1px solid palette(mid);
                outline: 0;
            }
        """)