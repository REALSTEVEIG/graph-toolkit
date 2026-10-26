"""Shared textbook example graphs."""

from __future__ import annotations

import pytest
from graphkit import Graph


@pytest.fixture
def clrs_dijkstra() -> Graph[str]:
    """Directed graph from CLRS (Fig. 24.6), source 's'.

    Known distances: s=0, t=8, x=9, y=5, z=7.
    """
    g: Graph[str] = Graph(directed=True)
    for u, v, w in [
        ("s", "t", 10), ("s", "y", 5),
        ("t", "x", 1), ("t", "y", 2),
        ("y", "t", 3), ("y", "x", 9), ("y", "z", 2),
        ("x", "z", 4),
        ("z", "s", 7), ("z", "x", 6),
    ]:
        g.add_edge(u, v, w)
    return g


@pytest.fixture
def clrs_bellman_ford() -> Graph[str]:
    """Directed graph with negative edges from CLRS (Fig. 24.4), source 's'.

    Known distances: s=0, t=2, x=4, y=7, z=-2.
    """
    g: Graph[str] = Graph(directed=True)
    for u, v, w in [
        ("s", "t", 6), ("s", "y", 7),
        ("t", "x", 5), ("t", "y", 8), ("t", "z", -4),
        ("x", "t", -2),
        ("y", "x", -3), ("y", "z", 9),
        ("z", "s", 2), ("z", "x", 7),
    ]:
        g.add_edge(u, v, w)
    return g


@pytest.fixture
def undirected_example() -> Graph[int]:
    """Small undirected weighted graph (classic 6-node Dijkstra example).

    From node 1: distances 1=0, 2=7, 3=9, 4=20, 5=20, 6=11.
    """
    g: Graph[int] = Graph()
    for u, v, w in [
        (1, 2, 7), (1, 3, 9), (1, 6, 14),
        (2, 3, 10), (2, 4, 15),
        (3, 4, 11), (3, 6, 2),
        (4, 5, 6), (5, 6, 9),
    ]:
        g.add_edge(u, v, w)
    return g
