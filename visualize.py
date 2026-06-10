"""Render the optimized route on an ARK-styled map using PyQtGraph."""

import math
from typing import Callable, List, Tuple

import pyqtgraph as pg
from PyQt6.QtCore import Qt

_PADDING = 5.0

# If a point is within this GPS distance of the PREVIOUS labeled point, skip it.
# Only the immediately preceding label is checked so distant-but-coincident
# earlier steps (e.g. step 1 near step 7) never suppress a label.
_CLUSTER_RADIUS = 1.0

# Estimated full-label bounding box in GPS units (for collision detection).
_LABEL_W = 12.0
_LABEL_H = 2.5

# Exclusion zone around every waypoint dot so labels don't land on top of them.
_DOT_EXCL = 3.0  # GPS-unit radius

# Radii and angle deltas tried when searching for a free label slot.
_LABEL_RADII = [4.0, 7.0, 10.0, 14.0]
_ANGLE_DELTAS = [0, math.pi/4, -math.pi/4, math.pi/2, -math.pi/2,
                 3*math.pi/4, -3*math.pi/4, math.pi]


def _find_label_pos(
    lat: float, lon: float,
    lat_mid: float, lon_mid: float,
    blocked: list,
) -> tuple[float, float]:
    """Return a (cx, cy) in GPS space clear of every box in *blocked*."""
    pref = math.atan2(lat - lat_mid, lon - lon_mid)
    for radius in _LABEL_RADII:
        for delta in _ANGLE_DELTAS:
            cx = lon + radius * math.cos(pref + delta)
            cy = lat + radius * math.sin(pref + delta)
            bx0, by0 = cx - _LABEL_W / 2, cy - _LABEL_H / 2
            bx1, by1 = cx + _LABEL_W / 2, cy + _LABEL_H / 2
            if not any(
                not (bx1 < px0 or bx0 > px1 or by1 < py0 or by0 > py1)
                for px0, py0, px1, py1 in blocked
            ):
                return cx, cy
    return lon + _LABEL_RADII[0], lat   # fallback


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

    # ── Labels: one per cluster, never on top of a dot ────────────────────────
    lat_mid = (min(lats) + max(lats)) / 2
    lon_mid = (min(lons) + max(lons)) / 2

    # Every dot is a blocked zone so labels can't land on top of waypoints.
    dot_blocks = [
        (lon - _DOT_EXCL, lat - _DOT_EXCL,
         lon + _DOT_EXCL, lat + _DOT_EXCL)
        for lat, lon in zip(lats, lons)
    ]

    placed_boxes: list[tuple[float, float, float, float]] = []
    labeled_positions: list[tuple[float, float]] = []   # (lat, lon) of labeled pts

    for step, (lat, lon) in enumerate(zip(lats, lons)):
        # Suppress only if the LAST labeled point is nearby — earlier steps
        # in different parts of the map never affect this decision.
        if labeled_positions:
            ly, lx = labeled_positions[-1]
            if ((lat - ly) ** 2 + (lon - lx) ** 2) ** 0.5 < _CLUSTER_RADIUS:
                continue

        labeled_positions.append((lat, lon))

        # Place label avoiding other labels AND all dot exclusion zones
        blocked = placed_boxes + dot_blocks
        cx, cy = _find_label_pos(lat, lon, lat_mid, lon_mid, blocked)
        placed_boxes.append((cx - _LABEL_W / 2, cy - _LABEL_H / 2,
                              cx + _LABEL_W / 2, cy + _LABEL_H / 2))

        plot.plot([lon, cx], [lat, cy],
                  pen=pg.mkPen("#334455", width=0.8))

        label = pg.TextItem(
            text=f"{step + 1}: {lat:.2f}, {lon:.2f}",
            color=(255, 255, 255),
            fill=pg.mkBrush(13, 31, 45, 180),
            anchor=(0.5, 0.5),
        )
        label.setPos(cx, cy)
        plot.addItem(label)

    # Fit view to waypoints AND label boxes so nothing is clipped
    all_x0 = [bx0 for bx0, _, _, _ in placed_boxes]
    all_y0 = [by0 for _, by0, _, _ in placed_boxes]
    all_x1 = [bx1 for _, _, bx1, _ in placed_boxes]
    all_y1 = [by1 for _, _, _, by1 in placed_boxes]
    view_x0 = min(min(lons), *all_x0) - _PADDING
    view_x1 = max(max(lons), *all_x1) + _PADDING
    view_y0 = min(min(lats), *all_y0) - _PADDING
    view_y1 = max(max(lats), *all_y1) + _PADDING
    plot.setXRange(view_x0, view_x1, padding=0)
    plot.setYRange(view_y0, view_y1, padding=0)

    # Realm overlays (hidden by default)
    realm_items = []
    for realm in _REALMS:
        corners = realm["corners"] + [realm["corners"][0]]
        rx = [lon for _lat, lon in corners]
        ry = [lat for lat, _lon in corners]
        item = plot.plot(
            rx, ry,
            pen=pg.mkPen(realm["color"], width=1.5, style=Qt.PenStyle.DashLine),
            name=realm["label"],
        )
        item.setVisible(False)
        realm_items.append(item)

    def toggle_realms() -> None:
        visible = not realm_items[0].isVisible()
        for item in realm_items:
            item.setVisible(visible)

    return plot, toggle_realms
