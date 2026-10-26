"""Minimum spanning tree via Prim's algorithm."""

from __future__ import annotations

import heapq
import itertools
from collections.abc import Hashable
from typing import TypeVar

from .graph import Graph

N = TypeVar("N", bound=Hashable)


def prim_mst(graph: Graph[N]) -> list[tuple[N, N, float]]:
    """Return the edges of a minimum spanning forest of an undirected graph.

    Prim's algorithm grows a tree from a start node, always adding the
    cheapest edge that connects the tree to a new node. If the graph is
    disconnected, the algorithm restarts from each unvisited node, so the
    result is a minimum spanning *forest* (one tree per component).
    Negative weights are allowed. Self-loops are never selected.

    Returns:
        A list of ``(u, v, weight)`` edges, where ``u`` was already in the
        tree when the edge was chosen.

    Raises:
        ValueError: If the graph is directed.
    """
    if graph.directed:
        raise ValueError("prim_mst requires an undirected graph")

    visited: set[N] = set()
    tree: list[tuple[N, N, float]] = []
    counter = itertools.count()

    for start in graph:
        if start in visited:
            continue
        visited.add(start)
        heap: list[tuple[float, int, N, N]] = [
            (w, next(counter), start, v) for v, w in graph.neighbor_items(start)
        ]
        heapq.heapify(heap)
        while heap:
            w, _, u, v = heapq.heappop(heap)
            if v in visited:
                continue
            visited.add(v)
            tree.append((u, v, w))
            for nxt, nw in graph.neighbor_items(v):
                if nxt not in visited:
                    heapq.heappush(heap, (nw, next(counter), v, nxt))
    return tree
