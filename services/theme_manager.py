from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QPalette,
)

try:
    from qdarktheme import load_stylesheet
    QDARKTHEME_AVAILABLE = True
except ImportError:
    QDARKTHEME_AVAILABLE = False

from services.icons import ICON_BUTTON_HEIGHT


# Padding vertical et min-height (boite de contenu)
# des boutons texte, pour une hauteur totale egale
# a ICON_BUTTON_HEIGHT (bordure de 1px de chaque cote).
BUTTON_PADDING_VERTICAL = 2

BUTTON_MIN_HEIGHT = (
    ICON_BUTTON_HEIGHT
    - 2 * BUTTON_PADDING_VERTICAL
    - 2
)


# Feuilles de style qdarktheme mises en cache. En binaire
# compile (Nuitka), l'import paresseux des ressources
# d'icones d'un theme, declenche par load_stylesheet au
# moment du changement de theme, provoque un crash natif.
# Charger les deux themes une fois au demarrage (contexte
# calme) et memoriser les feuilles de style evite tout
# import qdarktheme ulterieur : le changement de theme
# n'applique plus qu'un setStyleSheet deja construit.
_STYLESHEET_CACHE = {}


def _qdarktheme_stylesheet(theme):
    if theme not in _STYLESHEET_CACHE:
        from qdarktheme import load_stylesheet

        _STYLESHEET_CACHE[theme] = (
            load_stylesheet(
                theme=theme
            )
        )

    return _STYLESHEET_CACHE[theme]


class ThemeManager:
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"

    @staticmethod
    def apply_theme(app, theme):
        """
        Applique le theme selectionne a l'application.
        
        Args:
            app: QApplication instance
            theme: ThemeManager.SYSTEM, ThemeManager.LIGHT, or ThemeManager.DARK
        """
        if theme == ThemeManager.SYSTEM:
            ThemeManager.apply_system(app)
        elif theme == ThemeManager.DARK:
            ThemeManager.apply_dark(app)
        elif theme == ThemeManager.LIGHT:
            ThemeManager.apply_light(app)

    @staticmethod
    def preload_style_sheets():
        """
        Charge les feuilles de style des deux themes
        (qdarktheme). A appeler une fois au demarrage de
        l'application, apres creation du QApplication.
        """
        if QDARKTHEME_AVAILABLE:
            _qdarktheme_stylesheet("dark")
            _qdarktheme_stylesheet("light")

    @staticmethod
    def apply_system(app):
        """
        Applique le theme correspondant au theme systeme.
        Detecte automatiquement si le systeme est en mode clair ou sombre.
        """
        color_scheme = app.styleHints().colorScheme()
        
        if color_scheme == Qt.ColorScheme.Dark:
            ThemeManager.apply_dark(app)
        else:
            ThemeManager.apply_light(app)

    @staticmethod
    def _get_global_stylesheet(theme_type):
        """
        Retourne un stylesheet CSS pour personnaliser le fond général de l'interface.
        Pour le thème clair, remplace le blanc pur par un gris très clair.
        """
        if theme_type == "light":
            return """
                /* Fond général de l'application */
                QMainWindow, QWidget, QDialog, QFrame {
                    background-color: #fafafa;
                }
                /* Zone de contenu */
                QMainWindow {
                    background-color: #f8f8f8;
                }
                /* Zones de saisie */
                QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QListView, QTreeView {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                }
                /* Panneaux et conteneurs */
                QFrame, QGroupBox {
                    background-color: #f8f8f8;
                }
            """
        else:
            # Theme sombre : garder les couleurs par défaut de qdarktheme
            return ""

    @staticmethod
    def _get_button_stylesheet(theme_type):
        """
        Retourne un stylesheet CSS pour personnaliser les boutons.
        Corrige :
        - Texte des boutons en blanc (sombre) ou noir (clair) selon le theme
        - Fond des boutons en gris clair au lieu de blanc pour le theme light
        - Hauteur des boutons pilotee par ICON_BUTTON_HEIGHT
        (services/icons.py)
        """
        if theme_type == "dark":
            # Theme sombre : texte blanc, fond gris foncé
            return f"""
                QPushButton {{
                    color: #f0f0f0;
                    background-color: #373737;
                    border: 1px solid #5f5f5f;
                    border-radius: 4px;
                    padding: {BUTTON_PADDING_VERTICAL}px 12px;
                    min-height: {BUTTON_MIN_HEIGHT}px;
                }}
                QPushButton:hover {{
                    background-color: #4a4a4a;
                }}
                QPushButton:pressed {{
                    background-color: #2a2a2a;
                }}
                QPushButton:disabled {{
                    color: #828282;
                    background-color: #323232;
                }}
            """
        else:
            # Theme clair : texte noir, fond gris clair élégant
            return f"""
                QPushButton {{
                    color: #191919;
                    background-color: #f5f5f5;
                    border: 1px solid #a0a0a0;
                    border-radius: 4px;
                    padding: {BUTTON_PADDING_VERTICAL}px 12px;
                    min-height: {BUTTON_MIN_HEIGHT}px;
                }}
                QPushButton:hover {{
                    background-color: #e5e5e5;
                }}
                QPushButton:pressed {{
                    background-color: #d5d5d5;
                }}
                QPushButton:disabled {{
                    color: #828282;
                    background-color: #e8e8e8;
                }}
            """

    @staticmethod
    def apply_dark(app):
        """
        Applique le theme sombre utilisant qdarktheme.
        """
        if QDARKTHEME_AVAILABLE:
            # Utiliser qdarktheme pour un theme sombre moderne
            app.setStyle("Fusion")
            dark_stylesheet = _qdarktheme_stylesheet("dark")
            # Ajouter des ajustements pour les boutons et le fond
            dark_stylesheet += ThemeManager._get_global_stylesheet("dark")
            dark_stylesheet += ThemeManager._get_button_stylesheet("dark")
            app.setStyleSheet(dark_stylesheet)
        else:
            # Fallback au theme personnalise si qdarktheme n'est pas disponible
            ThemeManager._apply_dark_fallback(app)

    @staticmethod
    def apply_light(app):
        """
        Applique le theme clair utilisant qdarktheme.
        """
        if QDARKTHEME_AVAILABLE:
            # Utiliser qdarktheme pour un theme clair moderne
            app.setStyle("Fusion")
            light_stylesheet = _qdarktheme_stylesheet("light")
            # Ajouter des ajustements pour le fond et les boutons
            light_stylesheet += ThemeManager._get_global_stylesheet("light")
            light_stylesheet += ThemeManager._get_button_stylesheet("light")
            app.setStyleSheet(light_stylesheet)
        else:
            # Fallback au theme personnalise si qdarktheme n'est pas disponible
            ThemeManager._apply_light_fallback(app)

    @staticmethod
    def _apply_dark_fallback(app):
        """
        Methode de fallback pour le theme sombre.
        Utilise la palette personnalisee originale.
        """
        app.setStyle("Fusion")
        
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

        app.setPalette(palette)
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
    def _apply_light_fallback(app):
        """
        Methode de fallback pour le theme clair.
        Utilise la palette personnalisee originale.
        """
        app.setStyle("Fusion")

        palette = QPalette()

        # Fenetres et panneaux
        palette.setColor(
            QPalette.ColorRole.Window,
            QColor(245, 245, 245)
        )
        palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor(25, 25, 25)
        )

        # Zones de saisie / listes
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

        # Boutons
        palette.setColor(
            QPalette.ColorRole.Button,
            QColor(240, 240, 240)
        )
        palette.setColor(
            QPalette.ColorRole.ButtonText,
            QColor(25, 25, 25)
        )

        # Texte secondaire / separateurs
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

        # Selection
        palette.setColor(
            QPalette.ColorRole.Highlight,
            QColor(42, 125, 220)
        )
        palette.setColor(
            QPalette.ColorRole.HighlightedText,
            QColor(255, 255, 255)
        )

        # Liens
        palette.setColor(
            QPalette.ColorRole.Link,
            QColor(42, 125, 220)
        )
        palette.setColor(
            QPalette.ColorRole.LinkVisited,
            QColor(90, 70, 160)
        )

        # Tooltips
        palette.setColor(
            QPalette.ColorRole.ToolTipBase,
            QColor(255, 255, 220)
        )
        palette.setColor(
            QPalette.ColorRole.ToolTipText,
            QColor(25, 25, 25)
        )

        # Texte tres contraste
        palette.setColor(
            QPalette.ColorRole.BrightText,
            QColor(255, 255, 255)
        )
        
        # Champs de saisie et listes deroulantes.
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
        
        # Controles desactives.
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

        app.setPalette(palette)

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


#
# P16-bis, 2ᵉ série (spec correctifs §9) : couleurs de
# surlignage définies par thème — aucun jaune clair
# partagé entre les thèmes, texte lisible sur le fond
# surligné (contraste AA minimum).
#

COULEUR_SURLIGNAGE_MOT_CLAIR = "#FFF3B0"
COULEUR_SURLIGNAGE_MOT_SOMBRE = "#6B5300"

COULEUR_BLOC_JOUE_CLAIR = "#2196F3"
COULEUR_BLOC_JOUE_SOMBRE = "#64B5F6"


def est_sombre(widget) -> bool:
    """
    Résout le thème effectif d'un widget : le
    réglage « system » suit la luminosité de la
    palette courante (recalculée à chaque appel —
    un changement de thème est immédiatement
    pris en compte).
    """

    if widget is None:
        return False

    return (
        widget.palette()
        .window()
        .color()
        .lightness()
        < 128
    )


def couleurs_surlignage(sombre: bool) -> dict:
    """
    Couleurs de surlignage du thème courant :
    - « mot » : fond du mot lu (E1.3) ;
    - « bloc » : surbrillance du bloc en cours de
      lecture (§8.3).

    Paires texte/fond par thème (contraste AA) :
    - clair : texte #191919 sur fond #FFF3B0 ;
    - sombre : texte clair du thème sur fond
      #6B5300 (ambre sombre — le jaune clair
      disparaît du thème sombre).
    """

    if sombre:
        return {
            "mot": COULEUR_SURLIGNAGE_MOT_SOMBRE,
            "bloc": COULEUR_BLOC_JOUE_SOMBRE,
        }

    return {
        "mot": COULEUR_SURLIGNAGE_MOT_CLAIR,
        "bloc": COULEUR_BLOC_JOUE_CLAIR,
    }
