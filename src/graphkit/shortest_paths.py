"""Weighted shortest-path algorithms: Dijkstra, Bellman-Ford and A*.

Design choice for unreachable nodes
-----------------------------------
The *single-source* functions (:func:`dijkstra`, :func:`bellman_ford`)
return dictionaries that contain **only reachable nodes**; an unreachable
node is simply absent. The *point-to-point* functions
(:func:`shortest_path`, :func:`astar`) raise :class:`NoPathError` when the
target cannot be reached. An exception was chosen over returning ``None``
because "no route exists" is usually a case the caller must handle, and an
exception cannot be silently ignored the way a ``None`` can.
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections.abc import Callable, Hashable
from typing import TypeVar

from .exceptions import (
    NegativeCycleError,
    NegativeWeightError,
    NodeNotFoundError,
    NoPathError,
)
from .graph import Graph

N = TypeVar("N", bound=Hashable)


def _require(graph: Graph[N], node: N) -> None:
    if not graph.has_node(node):
        raise NodeNotFoundError(node)


def _check_non_negative(graph: Graph[N]) -> None:
    for u, v, w in graph.edges():
        if w < 0:
            raise NegativeWeightError(u, v, w)


def reconstruct_path(predecessors: dict[N, N | None], target: N) -> list[N]:
    """Follow predecessor links back from ``target`` and return the path.

    Args:
        predecessors: Mapping produced by :func:`dijkstra` or
            :func:`bellman_ford`; the source maps to ``None``.
        target: The node to build a path to.

    Raises:
        KeyError: If ``target`` is not in ``predecessors`` (unreachable).
    """
    path: list[N] = []
    current: N | None = target
    while current is not None:
        path.append(current)
        current = predecessors[current]
    path.reverse()
    return path


def dijkstra(
    graph: Graph[N], source: N
) -> tuple[dict[N, float], dict[N, N | None]]:
    """Compute shortest distances from ``source`` to every reachable node.

    Uses a binary heap (:mod:`heapq`) with *lazy deletion*: instead of
    decreasing a key inside the heap (which ``heapq`` does not support), a
    new entry is pushed and stale entries are skipped when popped.

    A tie-breaking counter is stored in each heap entry so that nodes are
    never compared with each other; this lets nodes be any hashable type,
    even ones that do not support ``<``.

    Args:
        graph: Graph whose edge weights are all non-negative.
        source: Start node.

    Returns:
        ``(distances, predecessors)``. ``distances[v]`` is the cost of the
        cheapest path to ``v``; ``predecessors[v]`` is the node before
        ``v`` on that path (``None`` for the source). Unreachable nodes are
        absent from both dictionaries.

    Raises:
        NodeNotFoundError: If ``source`` is not in the graph.
        NegativeWeightError: If any edge has a negative weight.
    """
    _require(graph, source)
    _check_non_negative(graph)

    dist: dict[N, float] = {source: 0.0}
    pred: dict[N, N | None] = {source: None}
    done: set[N] = set()
    counter = itertools.count()
    heap: list[tuple[float, int, N]] = [(0.0, next(counter), source)]

    while heap:
        d, _, node = heapq.heappop(heap)
        if node in done:
            continue  # stale entry left behind by lazy deletion
        done.add(node)
        for nbr, w in graph.neighbor_items(node):
            new_d = d + w
            if new_d < dist.get(nbr, math.inf):
                dist[nbr] = new_d
                pred[nbr] = node
                heapq.heappush(heap, (new_d, next(counter), nbr))
    return dist, pred


def shortest_path(graph: Graph[N], source: N, target: N) -> tuple[list[N], float]:
    """Return the cheapest path from ``source`` to ``target`` and its cost.

    Runs :func:`dijkstra`, so all weights must be non-negative.

    Returns:
        ``(path, cost)`` where ``path`` starts at ``source`` and ends at
        ``target``.

    Raises:
        NodeNotFoundError: If ``source`` or ``target`` is not in the graph.
        NegativeWeightError: If any edge has a negative weight.
        NoPathError: If ``target`` is unreachable from ``source``.
    """
    _require(graph, target)
    dist, pred = dijkstra(graph, source)
    if target not in dist:
        raise NoPathError(source, target)
    return reconstruct_path(pred, target), dist[target]


def bellman_ford(
    graph: Graph[N], source: N
) -> tuple[dict[N, float], dict[N, N | None]]:
    """Compute shortest distances from ``source``, allowing negative weights.

    Relaxes every edge up to ``V - 1`` times (stopping early if a full pass
    changes nothing). If one more pass could still shorten a distance, a
    negative cycle is reachable from ``source``.

    Note that in an undirected graph a single negative edge is itself a
    negative cycle (go back and forth along it), so it will be reported.

    Returns:
        ``(distances, predecessors)`` in the same format as
        :func:`dijkstra`; unreachable nodes are absent.

    Raises:
        NodeNotFoundError: If ``source`` is not in the graph.
        NegativeCycleError: If a negative cycle is reachable from ``source``.
    """
    _require(graph, source)

    edges = list(graph.edges())
    if not graph.directed:
        edges += [(v, u, w) for u, v, w in edges if u != v]

    dist: dict[N, float] = {source: 0.0}
    pred: dict[N, N | None] = {source: None}

    for _ in range(len(graph) - 1):
        changed = False
        for u, v, w in edges:
            if u in dist and dist[u] + w < dist.get(v, math.inf):
                dist[v] = dist[u] + w
                pred[v] = u
                changed = True
        if not changed:
            break

    for u, v, w in edges:
        if u in dist and dist[u] + w < dist.get(v, math.inf):
            raise NegativeCycleError(
                f"negative cycle reachable from {source!r} (via edge {u!r} -> {v!r})"
            )
    return dist, pred


def astar(
    graph: Graph[N],
    source: N,
    target: N,
    heuristic: Callable[[N, N], float],
) -> tuple[list[N], float]:
    """Find the cheapest path using A* search.

    A* is Dijkstra guided by a heuristic: nodes are explored in order of
    ``cost so far + heuristic(node, target)``. The result is optimal when
    the heuristic is *admissible* (never overestimates the remaining cost)
    and *consistent* (``h(u) <= w(u, v) + h(v)`` for every edge). With
    ``heuristic = lambda u, t: 0`` A* behaves exactly like Dijkstra.

    Args:
        graph: Graph whose edge weights are all non-negative.
        source: Start node.
        target: Goal node.
        heuristic: Estimate of the remaining cost from a node to ``target``.

    Returns:
        ``(path, cost)``.

    Raises:
        NodeNotFoundError: If ``source`` or ``target`` is not in the graph.
        NegativeWeightError: If any edge has a negative weight.
        NoPathError: If ``target`` is unreachable from ``source``.
    """
    _require(graph, source)
    _require(graph, target)
    _check_non_negative(graph)

    g_score: dict[N, float] = {source: 0.0}
    pred: dict[N, N | None] = {source: None}
    done: set[N] = set()
    counter = itertools.count()
    heap: list[tuple[float, int, N]] = [
        (heuristic(source, target), next(counter), source)
    ]

    while heap:
        _, _, node = heapq.heappop(heap)
        if node == target:
            return reconstruct_path(pred, target), g_score[target]
        if node in done:
            continue
        done.add(node)
        for nbr, w in graph.neighbor_items(node):
            new_g = g_score[node] + w
            if new_g < g_score.get(nbr, math.inf):
                g_score[nbr] = new_g
                pred[nbr] = node
                f = new_g + heuristic(nbr, target)
                heapq.heappush(heap, (f, next(counter), nbr))
    raise NoPathError(source, target)
