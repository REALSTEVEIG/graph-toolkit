"""Tests for Prim's minimum spanning tree."""

from __future__ import annotations

import pytest
from graphkit import Graph, connected_components, prim_mst


def test_prim_clrs() -> None:
    """CLRS Fig. 23.1: MST weight is 37."""
    g: Graph[str] = Graph()
    for u, v, w in [
        ("a", "b", 4), ("a", "h", 8), ("b", "c", 8), ("b", "h", 11),
        ("c", "d", 7), ("c", "f", 4), ("c", "i", 2), ("d", "e", 9),
        ("d", "f", 14), ("e", "f", 10), ("f", "g", 2), ("g", "h", 1),
        ("g", "i", 6), ("h", "i", 7),
    ]:
        g.add_edge(u, v, w)
    tree = prim_mst(g)
    assert len(tree) == len(g) - 1
    assert sum(w for _, _, w in tree) == 37


def test_prim_disconnected_forest_and_self_loop() -> None:
    g: Graph[int] = Graph()
    g.add_edge(1, 2, 3)
    g.add_edge(2, 3, 1)
    g.add_edge(1, 3, 5)
    g.add_edge(4, 5, -2)
    g.add_edge(4, 4, -10)
    g.add_node(6)
    tree = prim_mst(g)
    assert len(tree) == len(g) - len(connected_components(g))
    assert sum(w for _, _, w in tree) == 2
    assert all(u != v for u, v, _ in tree)


def test_prim_single_node() -> None:
    g: Graph[int] = Graph()
    g.add_node(1)
    assert prim_mst(g) == []


def test_prim_directed_raises() -> None:
    with pytest.raises(ValueError):
        prim_mst(Graph(directed=True))
