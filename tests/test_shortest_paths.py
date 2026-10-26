"""Tests for Dijkstra, Bellman-Ford and A*."""

from __future__ import annotations

import math
import random

import pytest
from graphkit import (
    Graph,
    NegativeCycleError,
    NegativeWeightError,
    NodeNotFoundError,
    NoPathError,
    astar,
    bellman_ford,
    dijkstra,
    reconstruct_path,
    shortest_path,
)

CLRS_DIJKSTRA = {"s": 0, "t": 8, "x": 9, "y": 5, "z": 7}
CLRS_BF = {"s": 0, "t": 2, "x": 4, "y": 7, "z": -2}


def _path_cost(g: Graph[object], path: list[object]) -> float:
    return sum(g.weight(u, v) for u, v in zip(path, path[1:]))


# --- Dijkstra ------------------------------------------------------------

def test_dijkstra_clrs(clrs_dijkstra: Graph[str]) -> None:
    dist, pred = dijkstra(clrs_dijkstra, "s")
    assert dist == CLRS_DIJKSTRA
    assert pred == {"s": None, "t": "y", "x": "t", "y": "s", "z": "y"}


def test_shortest_path_clrs(clrs_dijkstra: Graph[str]) -> None:
    path, cost = shortest_path(clrs_dijkstra, "s", "x")
    assert path == ["s", "y", "t", "x"]
    assert cost == 9


def test_dijkstra_undirected(undirected_example: Graph[int]) -> None:
    dist, _ = dijkstra(undirected_example, 1)
    assert dist == {1: 0, 2: 7, 3: 9, 4: 20, 5: 20, 6: 11}
    path, cost = shortest_path(undirected_example, 1, 5)
    assert path == [1, 3, 6, 5]
    assert cost == 20


def test_dijkstra_direction_matters() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b", 1)
    assert shortest_path(g, "a", "b") == (["a", "b"], 1)
    with pytest.raises(NoPathError):
        shortest_path(g, "b", "a")

    u: Graph[str] = Graph()
    u.add_edge("a", "b", 1)
    assert shortest_path(u, "b", "a") == (["b", "a"], 1)


def test_dijkstra_unreachable_nodes_absent() -> None:
    g: Graph[str] = Graph()
    g.add_edge("a", "b", 1)
    g.add_edge("c", "d", 1)
    dist, pred = dijkstra(g, "a")
    assert set(dist) == set(pred) == {"a", "b"}
    with pytest.raises(NoPathError) as exc:
        shortest_path(g, "a", "d")
    assert (exc.value.source, exc.value.target) == ("a", "d")


def test_dijkstra_single_node_and_self_target() -> None:
    g: Graph[str] = Graph()
    g.add_node("a")
    assert dijkstra(g, "a") == ({"a": 0.0}, {"a": None})
    assert shortest_path(g, "a", "a") == (["a"], 0.0)


def test_dijkstra_self_loop_ignored() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "a", 0)
    g.add_edge("a", "b", 2)
    assert dijkstra(g, "a")[0] == {"a": 0, "b": 2}


def test_dijkstra_zero_weight_edges() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b", 0)
    g.add_edge("b", "c", 0)
    g.add_edge("a", "c", 1)
    assert shortest_path(g, "a", "c") == (["a", "b", "c"], 0)


def test_dijkstra_lazy_deletion_updates() -> None:
    """Node 'c' is pushed twice; the stale entry must be skipped."""
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "c", 10)
    g.add_edge("a", "b", 1)
    g.add_edge("b", "c", 1)
    g.add_edge("c", "d", 1)
    dist, pred = dijkstra(g, "a")
    assert dist["d"] == 3
    assert reconstruct_path(pred, "d") == ["a", "b", "c", "d"]


def test_dijkstra_unorderable_nodes() -> None:
    """Heap ties must not compare nodes, so non-orderable nodes work."""
    a, b, c = object(), object(), object()
    g: Graph[object] = Graph()
    g.add_edge(a, b, 1)
    g.add_edge(a, c, 1)
    dist, _ = dijkstra(g, a)
    assert dist == {a: 0, b: 1, c: 1}


def test_dijkstra_negative_weight_raises() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b", 1)
    g.add_edge("b", "c", -1)
    with pytest.raises(NegativeWeightError) as exc:
        dijkstra(g, "a")
    assert exc.value.weight == -1
    with pytest.raises(NegativeWeightError):
        shortest_path(g, "a", "c")


def test_dijkstra_missing_nodes_raise() -> None:
    g: Graph[str] = Graph()
    g.add_node("a")
    with pytest.raises(NodeNotFoundError):
        dijkstra(g, "x")
    with pytest.raises(NodeNotFoundError):
        shortest_path(g, "x", "a")
    with pytest.raises(NodeNotFoundError):
        shortest_path(g, "a", "x")


def test_reconstruct_path_unreachable_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        reconstruct_path({"a": None}, "z")


# --- Bellman-Ford --------------------------------------------------------

def test_bellman_ford_clrs(clrs_bellman_ford: Graph[str]) -> None:
    dist, pred = bellman_ford(clrs_bellman_ford, "s")
    assert dist == CLRS_BF
    assert reconstruct_path(pred, "z") == ["s", "y", "x", "t", "z"]


def test_bellman_ford_matches_dijkstra_on_clrs(clrs_dijkstra: Graph[str]) -> None:
    assert bellman_ford(clrs_dijkstra, "s")[0] == CLRS_DIJKSTRA


def test_bellman_ford_unreachable_absent() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b", -2)
    g.add_edge("c", "a", 1)
    assert bellman_ford(g, "a")[0] == {"a": 0, "b": -2}


def test_bellman_ford_single_node() -> None:
    g: Graph[str] = Graph()
    g.add_node("a")
    assert bellman_ford(g, "a") == ({"a": 0.0}, {"a": None})


def test_bellman_ford_negative_cycle_raises() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("s", "a", 1)
    g.add_edge("a", "b", -1)
    g.add_edge("b", "c", -1)
    g.add_edge("c", "a", 1)
    with pytest.raises(NegativeCycleError):
        bellman_ford(g, "s")


def test_bellman_ford_negative_self_loop_raises() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "a", -1)
    with pytest.raises(NegativeCycleError):
        bellman_ford(g, "a")


def test_bellman_ford_unreachable_negative_cycle_ok() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("s", "t", 1)
    g.add_edge("x", "y", -5)
    g.add_edge("y", "x", 1)
    assert bellman_ford(g, "s")[0] == {"s": 0, "t": 1}


def test_bellman_ford_undirected_negative_edge_is_cycle() -> None:
    g: Graph[str] = Graph()
    g.add_edge("a", "b", -1)
    with pytest.raises(NegativeCycleError):
        bellman_ford(g, "a")


def test_bellman_ford_missing_source() -> None:
    with pytest.raises(NodeNotFoundError):
        bellman_ford(Graph(), "x")


# --- Randomised cross-check ---------------------------------------------

def _random_graph(rng: random.Random, n: int, p: float, directed: bool) -> Graph[int]:
    g: Graph[int] = Graph(directed=directed)
    for i in range(n):
        g.add_node(i)
    for u in range(n):
        for v in range(n):
            if u != v and rng.random() < p:
                g.add_edge(u, v, rng.randint(0, 20))
    return g


@pytest.mark.parametrize("seed", range(25))
@pytest.mark.parametrize("directed", [True, False])
def test_dijkstra_matches_bellman_ford_random(seed: int, directed: bool) -> None:
    rng = random.Random(seed)
    g = _random_graph(rng, n=rng.randint(1, 30), p=rng.uniform(0.02, 0.3), directed=directed)
    source = rng.randrange(len(g))
    d_dist, d_pred = dijkstra(g, source)
    b_dist, _ = bellman_ford(g, source)
    assert d_dist.keys() == b_dist.keys()
    for node, d in d_dist.items():
        assert math.isclose(d, b_dist[node])
        # The reconstructed path must actually have the reported cost.
        path = reconstruct_path(d_pred, node)
        assert path[0] == source and path[-1] == node
        assert math.isclose(_path_cost(g, path), d)


# --- A* ------------------------------------------------------------------

def _grid(width: int, height: int, walls: set[tuple[int, int]]) -> Graph[tuple[int, int]]:
    g: Graph[tuple[int, int]] = Graph()
    for x in range(width):
        for y in range(height):
            if (x, y) in walls:
                continue
            g.add_node((x, y))
            for nx, ny in [(x + 1, y), (x, y + 1)]:
                if nx < width and ny < height and (nx, ny) not in walls:
                    g.add_edge((x, y), (nx, ny), 1)
    return g


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def test_astar_grid_matches_dijkstra() -> None:
    walls = {(1, 0), (1, 1), (1, 2), (3, 4), (3, 3), (3, 2)}
    g = _grid(5, 5, walls)
    path, cost = astar(g, (0, 0), (4, 0), _manhattan)
    _, d_cost = shortest_path(g, (0, 0), (4, 0))
    # (0,0)->(0,3): 3, ->(2,3): 2, ->(2,0): 3, ->(4,0): 2. Total 10.
    assert cost == d_cost == 10
    assert path[0] == (0, 0) and path[-1] == (4, 0)
    assert _path_cost(g, path) == cost  # type: ignore[arg-type]


def test_astar_zero_heuristic_is_dijkstra(clrs_dijkstra: Graph[str]) -> None:
    for target, expected in CLRS_DIJKSTRA.items():
        _, cost = astar(clrs_dijkstra, "s", target, lambda u, t: 0)
        assert cost == expected


def test_astar_errors() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b", 1)
    g.add_node("c")
    h = lambda u, t: 0
    with pytest.raises(NoPathError):
        astar(g, "a", "c", h)
    with pytest.raises(NodeNotFoundError):
        astar(g, "a", "x", h)
    with pytest.raises(NodeNotFoundError):
        astar(g, "x", "a", h)
    g.add_edge("b", "c", -1)
    with pytest.raises(NegativeWeightError):
        astar(g, "a", "c", h)
