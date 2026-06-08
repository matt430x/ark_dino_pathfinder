"""Render the optimized route on an ARK-styled map using PyQtGraph."""

from typing import Callable, List, Tuple

import pyqtgraph as pg
from PyQt6.QtCore import Qt

_PADDING = 5.0

# Minimum GPS-unit distance between two labeled waypoints.
# Points closer than this get their label suppressed to avoid overlap.
_MIN_LABEL_SEP = 4.0

_REALMS = [
    {
        "label": "Asgard",
        "color": "#ff5555",
        "corners": [(17.64, 5.30), (17.64, 56.16), (68.72, 56.16), (68.72, 5.30)],
    },
    {
        "label": "Jotunheim",
        "color": "#66ccff",
        "corners": [(57.10, 24.80), (56.11, 59.78), (89.70, 64.83), (97.42, 21.90)],
    },
    {
        "label": "Vanaheim",
        "color": "#44ee88",
        "corners": [(-7.17, 102.93), (27.12, 104.70), (33.06, 67.14), (-7.32, 67.23)],
    },
]


def plot_route(
    coords: List[Tuple[float, float]],
    route: List[int],
) -> Tuple[pg.PlotWidget, Callable]:
    """Build and return a PlotWidget with the route drawn on it.

    Must be called on the main Qt thread — PlotWidget is a QWidget.
    """
    lats = [coords[i][0] for i in route]
    lons = [coords[i][1] for i in route]

    total = sum(
        ((lats[i] - lats[i - 1]) ** 2 + (lons[i] - lons[i - 1]) ** 2) ** 0.5
        for i in range(1, len(lats))
    )

    plot = pg.PlotWidget(background="#0d1f2d")
    plot.setTitle(
        f"ARK Dino Pathfinder — {len(coords)} stops · distance {total:.1f}",
        color="#00ccdd", size="12pt",
    )

    for name in ("bottom", "left", "top", "right"):
        ax = plot.getAxis(name)
        ax.setPen(pg.mkPen("#1a3a4a"))
        ax.setTextPen(pg.mkPen("#aaccdd"))

    plot.getAxis("bottom").setLabel("Longitude (East →)")
    plot.getAxis("left").setLabel("Latitude (South ↓)")
    plot.showGrid(x=True, y=True, alpha=0.25)
    plot.invertY(True)

    # Left-drag pans, scroll wheel zooms — conventional map behaviour
    plot.getViewBox().setMouseMode(pg.ViewBox.PanMode)

    # Route line
    plot.plot(lons, lats, pen=pg.mkPen("#0088cc", width=1.8))

    # Waypoints
    plot.addItem(pg.ScatterPlotItem(
        x=lons, y=lats,
        pen=pg.mkPen("white", width=0.5),
        brush=pg.mkBrush(0, 204, 221, 210),
        size=9, symbol="o", pxMode=True,
    ))

    # Start marker
    plot.addItem(pg.ScatterPlotItem(
        x=[lons[0]], y=[lats[0]],
        pen=pg.mkPen("white", width=1),
        brush=pg.mkBrush("#00ff88"),
        size=16, symbol="star", pxMode=True,
    ))

    # Step labels — quadrant-aware anchors + overlap suppression
    lat_mid = (min(lats) + max(lats)) / 2
    lon_mid = (min(lons) + max(lons)) / 2
    labeled_positions: list[tuple[float, float]] = []

    for step, (lat, lon) in enumerate(zip(lats, lons)):
        # Skip if another label is already too close (would overlap)
        if any(
            ((lat - ly) ** 2 + (lon - lx) ** 2) ** 0.5 < _MIN_LABEL_SEP
            for ly, lx in labeled_positions
        ):
            continue
        labeled_positions.append((lat, lon))

        # Choose anchor so text always points toward the interior of the data
        # anchor (0,*) → text right of point; (1,*) → text left of point
        # anchor (*,0) → text below point;  (*,1) → text above point
        ah = 0 if lon <= lon_mid else 1   # left half: extend right; right half: extend left
        av = 1 if lat <= lat_mid else 0   # top half:  extend above; bottom half: extend below
        ox = 0.3 if ah == 0 else -0.3

        label = pg.TextItem(
            text=f"{step + 1}: {lat:.2f}, {lon:.2f}",
            color=(255, 255, 255),
            fill=pg.mkBrush(13, 31, 45, 180),
            anchor=(ah, av),
        )
        label.setPos(lon + ox, lat)
        plot.addItem(label)

    # Realm overlays (hidden by default, toggled by the Realms button)
    realm_items = []
    for realm in _REALMS:
        corners = realm["corners"] + [realm["corners"][0]]   # close polygon
        rx = [lon for _lat, lon in corners]
        ry = [lat for lat, _lon in corners]
        item = plot.plot(
            rx, ry,
            pen=pg.mkPen(realm["color"], width=1.5, style=Qt.PenStyle.DashLine),
            name=realm["label"],
        )
        item.setVisible(False)
        realm_items.append(item)

    # Fit view to waypoints
    plot.setXRange(min(lons) - _PADDING, max(lons) + _PADDING, padding=0)
    plot.setYRange(min(lats) - _PADDING, max(lats) + _PADDING, padding=0)

    def toggle_realms() -> None:
        visible = not realm_items[0].isVisible()
        for item in realm_items:
            item.setVisible(visible)

    return plot, toggle_realms
