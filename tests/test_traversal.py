"""Tests for BFS, DFS, unweighted shortest path, topological sort and components."""

from __future__ import annotations

import pytest
from graphkit import (
    Graph,
    GraphCycleError,
    NodeNotFoundError,
    NoPathError,
    bfs,
    bfs_shortest_path,
    connected_components,
    dfs,
    topological_sort,
)


@pytest.fixture
def tree() -> Graph[str]:
    r"""Undirected tree:

          a
         / \
        b   c
       / \   \
      d   e   f
    """
    g: Graph[str] = Graph()
    for u, v in [("a", "b"), ("a", "c"), ("b", "d"), ("b", "e"), ("c", "f")]:
        g.add_edge(u, v)
    return g


def test_bfs_level_order(tree: Graph[str]) -> None:
    assert bfs(tree, "a") == ["a", "b", "c", "d", "e", "f"]


def test_dfs_preorder(tree: Graph[str]) -> None:
    assert dfs(tree, "a") == ["a", "b", "d", "e", "c", "f"]


def test_dfs_matches_recursive_order_with_cycle() -> None:
    g: Graph[int] = Graph()
    for u, v in [(1, 2), (1, 3), (2, 3), (3, 4)]:
        g.add_edge(u, v)
    assert dfs(g, 1) == [1, 2, 3, 4]


def test_dfs_deep_graph_no_recursion_error() -> None:
    g: Graph[int] = Graph(directed=True)
    for i in range(10_000):
        g.add_edge(i, i + 1)
    assert len(dfs(g, 0)) == 10_001


def test_traversals_respect_direction() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b")
    g.add_edge("c", "a")
    assert bfs(g, "a") == ["a", "b"]
    assert dfs(g, "a") == ["a", "b"]
    assert bfs(g, "b") == ["b"]


def test_traversals_undirected_go_both_ways() -> None:
    g: Graph[str] = Graph()
    g.add_edge("a", "b")
    g.add_edge("c", "a")
    assert set(bfs(g, "b")) == {"a", "b", "c"}


def test_traversals_disconnected_and_self_loop() -> None:
    g: Graph[str] = Graph()
    g.add_edge("a", "a")
    g.add_edge("a", "b")
    g.add_node("z")
    assert bfs(g, "a") == ["a", "b"]
    assert dfs(g, "a") == ["a", "b"]
    assert bfs(g, "z") == ["z"]


def test_traversal_single_node() -> None:
    g: Graph[str] = Graph()
    g.add_node("x")
    assert bfs(g, "x") == ["x"]
    assert dfs(g, "x") == ["x"]


def test_bfs_shortest_path_fewest_edges() -> None:
    g: Graph[str] = Graph()
    # Long cheap route a-b-c-d vs short expensive route a-d (weights ignored).
    g.add_edge("a", "b", 1)
    g.add_edge("b", "c", 1)
    g.add_edge("c", "d", 1)
    g.add_edge("a", "d", 100)
    assert bfs_shortest_path(g, "a", "d") == ["a", "d"]


def test_bfs_shortest_path_source_equals_target() -> None:
    g: Graph[str] = Graph()
    g.add_node("a")
    assert bfs_shortest_path(g, "a", "a") == ["a"]


def test_bfs_shortest_path_directed_unreachable() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b")
    assert bfs_shortest_path(g, "a", "b") == ["a", "b"]
    with pytest.raises(NoPathError):
        bfs_shortest_path(g, "b", "a")


def test_bfs_shortest_path_disconnected() -> None:
    g: Graph[str] = Graph()
    g.add_node("a")
    g.add_node("b")
    with pytest.raises(NoPathError):
        bfs_shortest_path(g, "a", "b")


@pytest.mark.parametrize("func", [bfs, dfs])
def test_traversal_missing_source(func) -> None:  # type: ignore[no-untyped-def]
    g: Graph[str] = Graph()
    with pytest.raises(NodeNotFoundError):
        func(g, "x")


def test_bfs_shortest_path_missing_nodes() -> None:
    g: Graph[str] = Graph()
    g.add_node("a")
    with pytest.raises(NodeNotFoundError):
        bfs_shortest_path(g, "x", "a")
    with pytest.raises(NodeNotFoundError):
        bfs_shortest_path(g, "a", "x")


# --- topological sort ----------------------------------------------------

def _is_topological(g: Graph[str], order: list[str]) -> bool:
    pos = {node: i for i, node in enumerate(order)}
    return all(pos[u] < pos[v] for u, v, _ in g.edges())


def test_topological_sort_clrs_dressing() -> None:
    """CLRS Fig. 22.7: getting dressed."""
    g: Graph[str] = Graph(directed=True)
    for u, v in [
        ("undershorts", "pants"), ("undershorts", "shoes"),
        ("pants", "belt"), ("pants", "shoes"),
        ("belt", "jacket"), ("shirt", "belt"), ("shirt", "tie"),
        ("tie", "jacket"), ("socks", "shoes"),
    ]:
        g.add_edge(u, v)
    g.add_node("watch")
    order = topological_sort(g)
    assert sorted(order) == sorted(g.nodes())
    assert _is_topological(g, order)


def test_topological_sort_deterministic() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "c")
    g.add_edge("b", "c")
    g.add_edge("c", "d")
    assert topological_sort(g) == ["a", "b", "c", "d"]


def test_topological_sort_empty_and_single() -> None:
    g: Graph[str] = Graph(directed=True)
    assert topological_sort(g) == []
    g.add_node("x")
    assert topological_sort(g) == ["x"]


def test_topological_sort_cycle_raises() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", "a")
    with pytest.raises(GraphCycleError):
        topological_sort(g)


def test_topological_sort_self_loop_raises() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "a")
    with pytest.raises(GraphCycleError):
        topological_sort(g)


def test_topological_sort_undirected_raises() -> None:
    with pytest.raises(ValueError):
        topological_sort(Graph())


# --- connected components ------------------------------------------------

def test_connected_components() -> None:
    g: Graph[int] = Graph()
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(4, 5)
    g.add_node(6)
    g.add_edge(7, 7)
    assert connected_components(g) == [{1, 2, 3}, {4, 5}, {6}, {7}]


def test_connected_components_empty_and_single() -> None:
    g: Graph[int] = Graph()
    assert connected_components(g) == []
    g.add_node(1)
    assert connected_components(g) == [{1}]


def test_connected_components_directed_raises() -> None:
    with pytest.raises(ValueError):
        connected_components(Graph(directed=True))
