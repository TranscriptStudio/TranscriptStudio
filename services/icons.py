# services/icons.py

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QIcon,
    QPainter,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer

from services.resources import resource_path


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
