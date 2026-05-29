"""TSP solver: nearest-neighbor construction + 2-opt improvement."""

from typing import List, Tuple, Optional

import numpy as np
from scipy.spatial.distance import cdist


def solve_tsp(coords: List[Tuple[float, float]]) -> List[int]:
    """Return an ordered list of coordinate indices forming a short open path."""
    n = len(coords)
    if n <= 2:
        return list(range(n))

    dist = cdist(np.array(coords, dtype=float), np.array(coords, dtype=float))

    best: Optional[List[int]] = None
    best_cost = float("inf")
    for start in range(min(n, 8)):
        route = _nearest_neighbor(dist, n, start)
        cost = _cost(dist, route)
        if cost < best_cost:
            best_cost, best = cost, route

    return _two_opt(dist, best)  # type: ignore[arg-type]


def _nearest_neighbor(dist: np.ndarray, n: int, start: int) -> List[int]:
    visited = [False] * n
    route = [start]
    visited[start] = True
    for _ in range(n - 1):
        cur = route[-1]
        nxt = min((i for i in range(n) if not visited[i]), key=lambda i: dist[cur][i])
        route.append(nxt)
        visited[nxt] = True
    return route


def _cost(dist: np.ndarray, route: List[int]) -> float:
    return float(sum(dist[route[i]][route[i + 1]] for i in range(len(route) - 1)))


def _two_opt(dist: np.ndarray, route: List[int]) -> List[int]:
    """Iteratively reverse sub-segments while they reduce total distance."""
    n = len(route)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n - 1):
                delta = (
                    dist[route[i - 1]][route[j]]
                    + dist[route[i]][route[j + 1]]
                    - dist[route[i - 1]][route[i]]
                    - dist[route[j]][route[j + 1]]
                )
                if delta < -1e-10:
                    route[i : j + 1] = route[i : j + 1][::-1]
                    improved = True
    return route
