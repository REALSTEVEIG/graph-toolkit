"""Tests for the Graph data structure."""

from __future__ import annotations

import math

import pytest
from graphkit import EdgeNotFoundError, Graph, NodeNotFoundError


def test_empty_graph() -> None:
    g: Graph[str] = Graph()
    assert len(g) == 0
    assert g.number_of_nodes() == 0
    assert g.number_of_edges() == 0
    assert list(g) == []
    assert list(g.edges()) == []


def test_single_node() -> None:
    g: Graph[str] = Graph()
    g.add_node("a")
    g.add_node("a")  # idempotent
    assert g.nodes() == ["a"]
    assert "a" in g
    assert g.has_node("a")
    assert list(g.neighbors("a")) == []
    assert g.number_of_edges() == 0


def test_add_edge_creates_nodes_and_default_weight() -> None:
    g: Graph[str] = Graph()
    g.add_edge("a", "b")
    assert g.nodes() == ["a", "b"]
    assert g.weight("a", "b") == 1.0


def test_undirected_edge_is_symmetric() -> None:
    g: Graph[str] = Graph()
    g.add_edge("a", "b", 3)
    assert g.has_edge("a", "b") and g.has_edge("b", "a")
    assert g.weight("b", "a") == 3.0
    assert g.number_of_edges() == 1
    assert list(g.edges()) == [("a", "b", 3.0)]


def test_directed_edge_is_one_way() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b", 3)
    assert g.has_edge("a", "b")
    assert not g.has_edge("b", "a")
    assert g.number_of_edges() == 1
    assert list(g.neighbors("b")) == []


def test_overwrite_weight() -> None:
    g: Graph[str] = Graph()
    g.add_edge("a", "b", 1)
    g.add_edge("b", "a", 5)
    assert g.weight("a", "b") == 5.0
    assert g.number_of_edges() == 1


@pytest.mark.parametrize("directed", [True, False])
def test_self_loop_counting(directed: bool) -> None:
    g: Graph[str] = Graph(directed=directed)
    g.add_edge("a", "a", 2)
    g.add_edge("a", "b", 1)
    assert g.has_edge("a", "a")
    assert g.number_of_edges() == 2
    assert len(list(g.edges())) == 2


def test_remove_edge_undirected() -> None:
    g: Graph[str] = Graph()
    g.add_edge("a", "b")
    g.remove_edge("b", "a")
    assert not g.has_edge("a", "b") and not g.has_edge("b", "a")
    assert g.number_of_nodes() == 2


def test_remove_edge_directed_keeps_reverse() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b")
    g.add_edge("b", "a")
    g.remove_edge("a", "b")
    assert not g.has_edge("a", "b")
    assert g.has_edge("b", "a")


def test_remove_self_loop() -> None:
    g: Graph[str] = Graph()
    g.add_edge("a", "a")
    g.remove_edge("a", "a")
    assert g.number_of_edges() == 0


def test_remove_node_removes_incident_edges() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b")
    g.add_edge("c", "b")
    g.add_edge("b", "d")
    g.remove_node("b")
    assert "b" not in g
    assert g.number_of_edges() == 0
    assert g.nodes() == ["a", "c", "d"]


def test_neighbor_items_and_iteration_order() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "c", 2)
    g.add_edge("a", "b", 1)
    assert list(g.neighbors("a")) == ["c", "b"]
    assert list(g.neighbor_items("a")) == [("c", 2.0), ("b", 1.0)]
    assert list(g) == ["a", "c", "b"]


def test_has_edge_unknown_nodes_is_false() -> None:
    g: Graph[str] = Graph()
    assert not g.has_edge("x", "y")


def test_repr() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b")
    assert repr(g) == "Graph(directed, nodes=2, edges=1)"


def test_any_hashable_node_type() -> None:
    g: Graph[tuple[int, int]] = Graph()
    g.add_edge((0, 0), (0, 1))
    assert g.has_edge((0, 1), (0, 0))


# --- error paths ---------------------------------------------------------

def test_remove_missing_node_raises() -> None:
    g: Graph[str] = Graph()
    with pytest.raises(NodeNotFoundError) as exc:
        g.remove_node("x")
    assert exc.value.node == "x"


def test_remove_edge_missing_node_raises() -> None:
    g: Graph[str] = Graph()
    g.add_node("a")
    with pytest.raises(NodeNotFoundError):
        g.remove_edge("a", "x")


def test_remove_missing_edge_raises() -> None:
    g: Graph[str] = Graph()
    g.add_node("a")
    g.add_node("b")
    with pytest.raises(EdgeNotFoundError):
        g.remove_edge("a", "b")


def test_weight_errors() -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b")
    with pytest.raises(EdgeNotFoundError):
        g.weight("b", "a")
    with pytest.raises(NodeNotFoundError):
        g.weight("a", "x")


def test_neighbors_missing_node_raises() -> None:
    g: Graph[str] = Graph()
    with pytest.raises(NodeNotFoundError):
        g.neighbors("x")
    with pytest.raises(NodeNotFoundError):
        g.neighbor_items("x")


@pytest.mark.parametrize("bad", ["1", None, True, [1]])
def test_non_numeric_weight_raises(bad: object) -> None:
    g: Graph[str] = Graph()
    with pytest.raises(TypeError):
        g.add_edge("a", "b", bad)  # type: ignore[arg-type]
    assert len(g) == 0  # graph left unchanged


@pytest.mark.parametrize("bad", [math.inf, -math.inf, math.nan])
def test_non_finite_weight_raises(bad: float) -> None:
    g: Graph[str] = Graph()
    with pytest.raises(ValueError):
        g.add_edge("a", "b", bad)
