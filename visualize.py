"""Render the optimized route on an ARK-styled map using PyQtGraph."""

import math
from typing import Callable, List, Tuple

import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

_PADDING        = 8.0
_CLUSTER_RADIUS = 1.0
_BASE_FONT_SIZE = 7
_LABEL_DIST     = 1.0   # initial distance from waypoint to label center (GPS units)
_LABEL_W        = 7.0   # approximate label width  (GPS units) — used for overlap detection
_LABEL_H        = 2.5   # approximate label height (GPS units)
_NUDGE_EPS      = 0.05  # small extra separation added after exact overlap resolution
_MAX_SWEEPS     = 300   # safety cap on repulsion iterations


def _run_repulsion(entries: list) -> None:
    """Mutually repel overlapping label pairs until no overlaps remain."""
    n = len(entries)
    for _ in range(_MAX_SWEEPS):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                cx_a, cy_a = entries[i][3], entries[i][4]
                cx_b, cy_b = entries[j][3], entries[j][4]
                dx = cx_b - cx_a
                dy = cy_b - cy_a
                if abs(dx) >= _LABEL_W or abs(dy) >= _LABEL_H:
                    continue
                dist = math.hypot(dx, dy)
                if dist < 1e-9:
                    ux, uy, dist = 1.0, 0.0, 1.0
                else:
                    ux, uy = dx / dist, dy / dist
                f_x = _LABEL_W / abs(dx) if abs(dx) > 1e-9 else math.inf
                f_y = _LABEL_H / abs(dy) if abs(dy) > 1e-9 else math.inf
                d = (min(f_x, f_y) - 1) * dist / 2 + _NUDGE_EPS
                entries[i][3] -= d * ux
                entries[i][4] -= d * uy
                entries[j][3] += d * ux
                entries[j][4] += d * uy
                moved = True
        if not moved:
            break


def _segments_cross(p1, p2, p3, p4) -> bool:
    """True if segment p1→p2 properly crosses segment p3→p4."""
    def _z(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1, d2 = _z(p3, p4, p1), _z(p3, p4, p2)
    d3, d4 = _z(p1, p2, p3), _z(p1, p2, p4)
    return (
        ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and
        ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))
    )


def _run_order_correction(entries: list) -> None:
    """Swap label pairs whose displacement is going backward relative to their waypoints.

    For labels i and j: if dot(waypoint_j - waypoint_i, label_j - label_i) < 0,
    the labels are spatially inverted relative to the route — swap them.
    This catches ordering anomalies that crossing detection misses.
    """
    n = len(entries)
    for _ in range(_MAX_SWEEPS):
        swapped = False
        for i in range(n):
            for j in range(i + 1, n):
                dw_x = entries[j][2] - entries[i][2]  # waypoint lon delta
                dw_y = entries[j][1] - entries[i][1]  # waypoint lat delta
                dl_x = entries[j][3] - entries[i][3]  # label cx delta
                dl_y = entries[j][4] - entries[i][4]  # label cy delta
                if dw_x * dl_x + dw_y * dl_y < 0:
                    entries[i][3], entries[j][3] = entries[j][3], entries[i][3]
                    entries[i][4], entries[j][4] = entries[j][4], entries[i][4]
                    swapped = True
        if not swapped:
            break


def _run_route_cross_fix(entries: list, lats: list, lons: list) -> None:
    """For each label whose leader line crosses the route path, pull it to
    0.2 GPS units from its waypoint in the current leader direction."""
    route_segs = [
        ((lons[k], lats[k]), (lons[k + 1], lats[k + 1]))
        for k in range(len(lats) - 1)
    ]

    def leader_crosses_route(idx: int) -> bool:
        p = (entries[idx][2], entries[idx][1])
        l = (entries[idx][3], entries[idx][4])
        return any(_segments_cross(p, l, s1, s2) for s1, s2 in route_segs)

    n = len(entries)
    for _ in range(_MAX_SWEEPS):
        moved = False
        for i in range(n):
            if not leader_crosses_route(i):
                continue
            lat_i, lon_i = entries[i][1], entries[i][2]
            cx_i, cy_i   = entries[i][3], entries[i][4]
            dist = math.hypot(cx_i - lon_i, cy_i - lat_i)
            if dist <= 0.2:
                continue
            vx = (cx_i - lon_i) / dist
            vy = (cy_i - lat_i) / dist
            entries[i][3] = lon_i + vx * 0.2
            entries[i][4] = lat_i + vy * 0.2
            moved = True
        if not moved:
            break


def _run_uncrossing(entries: list) -> None:
    """Swap label positions for any pair whose leader lines cross.

    In 2D, swapping the two label endpoints always eliminates the crossing —
    it is geometrically guaranteed. Repeats until a full sweep finds no crossings.
    """
    n = len(entries)
    for _ in range(_MAX_SWEEPS):
        swapped = False
        for i in range(n):
            for j in range(i + 1, n):
                p_i = (entries[i][2], entries[i][1])  # waypoint (lon, lat)
                l_i = (entries[i][3], entries[i][4])  # label   (cx,  cy)
                p_j = (entries[j][2], entries[j][1])
                l_j = (entries[j][3], entries[j][4])
                if _segments_cross(p_i, l_i, p_j, l_j):
                    entries[i][3], entries[j][3] = entries[j][3], entries[i][3]
                    entries[i][4], entries[j][4] = entries[j][4], entries[i][4]
                    swapped = True
        if not swapped:
            break


def _label_direction(lats: list, lons: list, i: int) -> float:
    """Angle (radians) at which to place the label for route index i.

    Interior points: bisector of the two route lines, pointing away from the turn.
    End points: directly opposite the single emitted line.
    """
    n = len(lats)

    if i == 0:
        dx = lons[1] - lons[0]
        dy = lats[1] - lats[0]
        return math.atan2(-dy, -dx)

    if i == n - 1:
        dx = lons[i - 1] - lons[i]
        dy = lats[i - 1] - lats[i]
        return math.atan2(-dy, -dx)

    # Unit vector toward previous neighbor
    dx1 = lons[i - 1] - lons[i]
    dy1 = lats[i - 1] - lats[i]
    d1 = math.hypot(dx1, dy1)
    if d1:
        dx1, dy1 = dx1 / d1, dy1 / d1

    # Unit vector toward next neighbor
    dx2 = lons[i + 1] - lons[i]
    dy2 = lats[i + 1] - lats[i]
    d2 = math.hypot(dx2, dy2)
    if d2:
        dx2, dy2 = dx2 / d2, dy2 / d2

    # Sum points inward; negate for outward (away from the turn).
    bx = -(dx1 + dx2)
    by = -(dy1 + dy2)

    if math.hypot(bx, by) < 1e-9:
        # Straight line — bisector cancels; use perpendicular instead.
        bx, by = -dy1, dx1

    return math.atan2(by, bx)


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

    # ── Pass 1: bisector placement ────────────────────────────────────────────
    # entries: [step, waypoint_lat, waypoint_lon, label_cx, label_cy]
    # cx/cy are mutable so the repulsion pass can update them in place.
    entries = []
    last_labeled = None

    for step, (lat, lon) in enumerate(zip(lats, lons)):
        if last_labeled is not None:
            ly, lx = last_labeled
            if ((lat - ly) ** 2 + (lon - lx) ** 2) ** 0.5 < _CLUSTER_RADIUS:
                continue
        last_labeled = (lat, lon)

        angle = _label_direction(lats, lons, step)
        cx = lon + _LABEL_DIST * math.cos(angle)
        cy = lat + _LABEL_DIST * math.sin(angle)
        entries.append([step, lat, lon, cx, cy])

    # ── Pass 2: repulsion → uncross → order-correct → repulsion → route-cross-fix
    _run_repulsion(entries)                   # separate overlapping labels
    _run_uncrossing(entries)                  # swap pairs whose leader lines cross
    _run_order_correction(entries)            # swap pairs whose labels are spatially inverted
    _run_repulsion(entries)                   # clean up any overlaps introduced by swapping
    _run_route_cross_fix(entries, lats, lons) # reel in labels whose leader crosses the route

    # ── Draw ─────────────────────────────────────────────────────────────────
    plot.plot(lons, lats, pen=pg.mkPen("#0088cc", width=1.8))

    plot.addItem(pg.ScatterPlotItem(
        x=lons, y=lats,
        pen=pg.mkPen("white", width=0.5),
        brush=pg.mkBrush(0, 204, 221, 210),
        size=9, symbol="o", pxMode=True,
    ))

    plot.addItem(pg.ScatterPlotItem(
        x=[lons[0]], y=[lats[0]],
        pen=pg.mkPen("white", width=1),
        brush=pg.mkBrush("#00ff88"),
        size=16, symbol="star", pxMode=True,
    ))

    label_text_items = []
    for step, lat, lon, cx, cy in entries:
        plot.plot([lon, cx], [lat, cy], pen=pg.mkPen("#334455", width=0.8))
        label = pg.TextItem(
            text=f"{step + 1}: {lat:.1f}, {lon:.1f}",
            color=(255, 255, 255),
            fill=pg.mkBrush(13, 31, 45, 180),
            anchor=(0.5, 0.5),
        )
        label.setFont(QFont("Segoe UI", _BASE_FONT_SIZE))
        label.setPos(cx, cy)
        plot.addItem(label)
        label_text_items.append(label)

    plot.setXRange(min(lons) - _PADDING, max(lons) + _PADDING, padding=0)
    plot.setYRange(min(lats) - _PADDING, max(lats) + _PADDING, padding=0)

    # Font scaling
    _ref = [None]

    def _rescale_fonts(_vb=None, _r=None):
        vb = plot.getViewBox()
        try:
            vr = vb.viewRange()
            gps_w = abs(vr[0][1] - vr[0][0])
            px_w = vb.width()
            if px_w <= 0 or gps_w <= 0:
                return
            if _ref[0] is None:
                _ref[0] = (px_w, gps_w)
                return
            ref_px_w, ref_gps_w = _ref[0]
            scale = (px_w / gps_w) / (ref_px_w / ref_gps_w)
            size = max(5, round(_BASE_FONT_SIZE * scale))
            font = QFont("Segoe UI", size)
            for lbl in label_text_items:
                lbl.setFont(font)
        except Exception:
            pass

    plot.getViewBox().sigRangeChanged.connect(_rescale_fonts)

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
