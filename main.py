"""ARK Dino Pathfinder — extract coordinates from Dino Scanner screenshots and solve the route.

Usage:
    python main.py screenshot1.png [screenshot2.png ...] [--output route_map.png]
"""

import argparse
import sys
from pathlib import Path

from extract import extract_coordinates
from route import solve_tsp
from visualize import plot_route


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read ARK Dino Scanner screenshots, deduplicate coordinates, and plot the optimal visit route."
    )
    parser.add_argument("images", nargs="+", help="Path(s) to Dino Scanner screenshot(s)")
    parser.add_argument("--output", default="route_map.png", help="Output map image path (default: route_map.png)")
    args = parser.parse_args()

    missing = [p for p in args.images if not Path(p).exists()]
    if missing:
        print(f"File(s) not found: {', '.join(missing)}")
        sys.exit(1)

    print(f"Scanning {len(args.images)} screenshot(s)...")
    coords = extract_coordinates(args.images)

    if not coords:
        print("No coordinates found. Make sure your screenshots show the Dino Scanner table with Lat./Long. columns.")
        sys.exit(1)

    print(f"\nFound {len(coords)} unique location(s):")
    for i, (lat, lon) in enumerate(coords, 1):
        print(f"  {i:3d}.  Lat {lat:6.2f}  Long {lon:6.2f}")

    print("\nSolving route...")
    route = solve_tsp(coords)

    total = sum(
        (
            (coords[route[i]][0] - coords[route[i - 1]][0]) ** 2
            + (coords[route[i]][1] - coords[route[i - 1]][1]) ** 2
        ) ** 0.5
        for i in range(1, len(route))
    )

    print(f"\nOptimal visit order (total distance: {total:.1f} units):")
    for step, idx in enumerate(route, 1):
        lat, lon = coords[idx]
        print(f"  Step {step:3d}:  Lat {lat:6.2f}  Long {lon:6.2f}")

    plot_route(coords, route, args.output)


if __name__ == "__main__":
    main()
