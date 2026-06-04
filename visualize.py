"""Render the optimized route on an ARK-styled coordinate map."""

from typing import List, Tuple

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from adjustText import adjust_text

_PADDING = 5.0

# Fjordur realm boundaries in (lat, lon) = (y, x) format
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
    output_path: str = "route_map.png",
) -> None:
    """Draw and save the route map, then display it."""
    lats = [coords[i][0] for i in route]
    lons = [coords[i][1] for i in route]

    total = sum(
        ((lats[i] - lats[i - 1]) ** 2 + (lons[i] - lons[i - 1]) ** 2) ** 0.5
        for i in range(1, len(lats))
    )

    fig, ax = plt.subplots(figsize=(6, 6), facecolor="#0d1f2d")
    ax.set_facecolor("#0d1f2d")

    # Fit view to waypoints only — realm outlines are clipped at the edges
    ax.set_xlim(min(lons) - _PADDING, max(lons) + _PADDING)
    ax.set_ylim(min(lats) - _PADDING, max(lats) + _PADDING)
    ax.invert_yaxis()
    ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(10))
    ax.grid(color="#1a3a4a", linewidth=0.5, alpha=0.7)

    # Realm outlines drawn first so they sit behind the route
    realm_patches = []
    for realm in _REALMS:
        xy = [(lon, lat) for lat, lon in realm["corners"]]
        patch = mpatches.Polygon(
            xy,
            closed=True,
            fill=False,
            edgecolor=realm["color"],
            linewidth=1.5,
            linestyle="--",
            zorder=1,
            label=realm["label"],
        )
        ax.add_patch(patch)
        patch.set_visible(False)
        realm_patches.append(patch)

    ax.plot(lons, lats, "-", color="#0088cc", linewidth=1.8, alpha=0.7, zorder=2)
    ax.scatter(lons, lats, color="cyan", s=55, zorder=4, edgecolors="white", linewidths=0.5)
    ax.scatter([lons[0]], [lats[0]], color="#00ff88", s=200, zorder=6, marker="*", label="Start")

    texts = []
    for step, (lat, lon) in enumerate(zip(lats, lons)):
        t = ax.text(
            lon,
            lat,
            f"{step + 1}: {lat:.2f}, {lon:.2f}",
            fontsize=7,
            color="white",
            zorder=5,
            bbox=dict(boxstyle="round,pad=0.15", facecolor="#0d1f2d", alpha=0.6, linewidth=0),
        )
        texts.append(t)

    adjust_text(
        texts,
        x=lons,
        y=lats,
        ax=ax,
        expand=(1.4, 1.6),
        arrowprops=dict(arrowstyle="-", color="#aaccdd", lw=0.7),
    )

    ax.set_xlabel("Longitude (East →)", color="#aaccdd", fontsize=11)
    ax.set_ylabel("Latitude (South ↓)", color="#aaccdd", fontsize=11)
    ax.set_title(
        f"ARK Dino Pathfinder — {len(coords)} stops · distance {total:.1f}",
        color="cyan",
        fontsize=13,
        pad=10,
    )
    ax.tick_params(colors="#aaccdd")
    for spine in ax.spines.values():
        spine.set_edgecolor("#1a3a4a")
    legend = ax.legend(facecolor="#0d1f2d", labelcolor="white", framealpha=0.5, loc="upper right")
    legend.set_visible(False)

    def _toggle_overlays(event):
        if event.key in ("l", "L"):
            visible = not realm_patches[0].get_visible()
            for patch in realm_patches:
                patch.set_visible(visible)
            legend.set_visible(visible)
            fig.canvas.draw_idle()

    try:
        plt.rcParams["keymap.yscale"].remove("l")
    except ValueError:
        pass
    fig.canvas.mpl_connect("key_press_event", _toggle_overlays)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"\nMap saved: {output_path}")
    print("  Tip: press L in the map window to toggle realm outlines and legend.")
    plt.show()
