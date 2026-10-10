# services/icons.py

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QIcon,
    QPainter,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer

from services.resources import resource_path


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

    Le SVG doit porter l'ancre fill="#2942ff" sur
    son élément racine : elle est remplacée par la
    couleur demandée avant le rendu.
    """

    svg = (
        resource_path(svg_relative_path)
        .read_text(encoding="utf-8")
    )

    svg = svg.replace(
        'fill="#2942ff"',
        f'fill="{color}"'
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
