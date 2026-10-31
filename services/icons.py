# services/icons.py

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
    QGuiApplication,
)
from PySide6.QtSvg import QSvgRenderer

from services.resources import resource_path


# Couleur de teinte des icones selon le theme
# configure ('light' -> noir, 'dark' -> clair).
TEXT_COLOR_LIGHT_THEME = "#191919"

TEXT_COLOR_DARK_THEME = "#F0F0F0"

#
# Signe + / - des icones A+/A- : bleu, dans les
# DEUX themes (retour David 31/10, UI
# reformulation point 2 : les icones A+/A- y
# sont EXACTEMENT celles de la page
# transcription).
#
COULEUR_SIGNE_TEXTE = "#2A7DDC"


def make_text_size_icon(symbol) -> QIcon:
    """
    Icone A+/A- partagee (pages Transcription et
    Reformulation) : « A » a la couleur du texte
    du theme APPLIQUE, signe +/− en bleu.
    """

    pixmap = QPixmap(32, 32)

    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)

    painter.setRenderHint(
        QPainter.RenderHint.Antialiasing
    )

    text_color = QColor(
        text_color_effectif()
    )

    painter.setPen(QPen(text_color))

    font = QFont()
    font.setPixelSize(18)
    font.setWeight(QFont.Weight.DemiBold)

    painter.setFont(font)

    painter.drawText(2, 23, "A")

    painter.setPen(
        QPen(QColor(COULEUR_SIGNE_TEXTE))
    )

    symbol_font = QFont()
    symbol_font.setPixelSize(16)
    symbol_font.setWeight(QFont.Weight.Bold)

    painter.setFont(symbol_font)

    painter.drawText(18, 17, symbol)

    painter.end()

    return QIcon(pixmap)


def make_theme_text_color(theme, app=None):
    """
    Couleur de teinte adaptee au theme configure.
    'system' suit le schema de couleurs du systeme.

    La palette Qt ne reflete pas la stylesheet du
    theme (elle reste la palette par defaut du
    systeme) : elle ne doit pas etre utilisee pour
    teinter les icones.
    """

    if theme == "dark":

        return TEXT_COLOR_DARK_THEME

    if theme == "light":

        return TEXT_COLOR_LIGHT_THEME

    app = (
        app
        or QGuiApplication.instance()
    )

    if (

        app is not None

        and app.styleHints().colorScheme()
        == Qt.ColorScheme.Dark

    ):

        return TEXT_COLOR_DARK_THEME

    return TEXT_COLOR_LIGHT_THEME


def text_color_effectif() -> str:
    """
    Couleur de texte du thème EFFECTIVEMENT appliqué
    (P18.6-bis série 8, retour David 31/10, points 7
    et 8) : qdarktheme ne met PAS la QPalette à
    jour et le réglage « system » se lit mal quand
    l'OS et l'app divergent — les icônes et les
    textes peints à la main suivent le thème appliqué
    par ThemeManager, pas la palette ni le seul
    réglage configuré.
    """

    from services.theme_manager import (
        theme_actif,
    )

    actif = theme_actif()

    if actif == "dark":
        return TEXT_COLOR_DARK_THEME

    if actif == "light":
        return TEXT_COLOR_LIGHT_THEME

    from services.settings import SettingsManager

    return make_theme_text_color(
        SettingsManager().get_theme()
    )


# Dimensions des boutons d'icones (barre d'outils
# de l'editeur et fenetre de pretraitement audio).
# Ajuster ici pour retailler tous les boutons.
ICON_BUTTON_WIDTH = 40

ICON_BUTTON_HEIGHT = 25


def make_button_height_css(
    height,
    border_px=0,
    padding_css="0px"
):
    """Retourne les regles CSS (padding, min-height,
    max-height) fixant la hauteur totale d'un bouton.

    La stylesheet du theme impose son propre modele de
    taille (min-height + padding + bordure) qui depasse
    setFixedSize : la hauteur doit donc etre fixee en
    CSS pour s'appliquer reellement. En CSS, min-height
    et max-height s'entendent hors padding et bordure,
    d'ou la soustraction.
    """

    vertical_padding = 0

    first_value = (
        padding_css
        .split()[0]
        .replace("px", "")
    )

    if first_value:

        vertical_padding = int(
            first_value
        )

    content_height = (
        height
        - 2 * border_px
        - 2 * vertical_padding
    )

    return (
        f"padding: {padding_css};\n"
        f"min-height: {content_height}px;\n"
        f"max-height: {content_height}px;\n"
    )


def make_tinted_icon(
    color,
    svg_relative_path,
    size,
    device_pixel_ratio=2.0
):
    """Retourne l'icône SVG teintée avec la couleur donnée.

    Le SVG doit porter l'ancre #2942ff (sur fill
    ou stroke) : elle est remplacée par la couleur
    demandée avant le rendu.
    """

    svg = (
        resource_path(svg_relative_path)
        .read_text(encoding="utf-8")
    )

    svg = svg.replace(
        'fill="#2942ff"',
        f'fill="{color}"'
    )

    #
    # Ancre stroke : les icones du stepper portent
    # la couleur sur stroke (et non fill) — sans
    # ce remplacement l'icone restait au bleu ancre
    # sur la pastille bleue « en cours » (retour
    # David 31/10, point icone illisible).
    #
    svg = svg.replace(
        'stroke="#2942ff"',
        f'stroke="{color}"'
    )

    renderer = QSvgRenderer(
        svg.encode("utf-8")
    )

    pixmap = QPixmap(
        int(size * device_pixel_ratio),
        int(size * device_pixel_ratio)
    )

    pixmap.fill(
        Qt.GlobalColor.transparent
    )

    painter = QPainter(pixmap)

    painter.setRenderHint(
        QPainter.RenderHint.Antialiasing,
        True
    )

    renderer.render(painter)

    painter.end()

    pixmap.setDevicePixelRatio(
        device_pixel_ratio
    )

    return QIcon(pixmap)
