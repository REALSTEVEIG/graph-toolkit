"""The :class:`Graph` data structure.

A graph is stored as an adjacency map: a dictionary that maps every node to
a second dictionary, which maps each neighbour to the weight of the edge.

    {"a": {"b": 2.0, "c": 1.0}, "b": {}, "c": {"b": 0.5}}

This gives O(1) average-time node lookup, edge lookup and edge insertion,
and lets algorithms iterate over a node's neighbours in O(degree) time.
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Iterator
from typing import Generic, TypeVar

from .exceptions import EdgeNotFoundError, NodeNotFoundError

N = TypeVar("N", bound=Hashable)
"""Type variable for node labels. Any hashable value can be a node."""


def _validate_weight(weight: float) -> float:
    """Return ``weight`` as a float, rejecting non-numeric or non-finite values."""
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        raise TypeError(f"edge weight must be a number, got {type(weight).__name__}")
    if not math.isfinite(weight):
        raise ValueError(f"edge weight must be finite, got {weight!r}")
    return float(weight)


class Graph(Generic[N]):
    """A weighted graph that is either directed or undirected.

    In an undirected graph, adding the edge ``(u, v)`` makes ``v`` a
    neighbour of ``u`` *and* ``u`` a neighbour of ``v``, with the same
    weight. Self-loops (``u == v``) are allowed. Adding an edge that
    already exists overwrites its weight; parallel edges are not supported.

    Nodes and neighbours are iterated in insertion order, which makes the
    output of every algorithm in this package deterministic.

    Example:
        >>> g: Graph[str] = Graph(directed=True)
        >>> g.add_edge("a", "b", 2.5)
        >>> g.weight("a", "b")
        2.5
        >>> g.has_edge("b", "a")
        False
    """

    def __init__(self, directed: bool = False) -> None:
        """Create an empty graph.

        Args:
            directed: If ``True``, edges have a direction; otherwise every
                edge can be travelled both ways.
        """
        self._directed = directed
        self._adj: dict[N, dict[N, float]] = {}

    # ------------------------------------------------------------------
    # Basic properties
    # ------------------------------------------------------------------
    @property
    def directed(self) -> bool:
        """Whether the graph is directed."""
        return self._directed

    def __len__(self) -> int:
        """Return the number of nodes."""
        return len(self._adj)

    def __iter__(self) -> Iterator[N]:
        """Iterate over the nodes in insertion order."""
        return iter(self._adj)

    def __contains__(self, node: object) -> bool:
        """Return ``True`` if ``node`` is in the graph."""
        return node in self._adj

    def __repr__(self) -> str:
        kind = "directed" if self._directed else "undirected"
        return (
            f"Graph({kind}, nodes={self.number_of_nodes()}, "
            f"edges={self.number_of_edges()})"
        )

    def number_of_nodes(self) -> int:
        """Return the number of nodes in the graph."""
        return len(self._adj)

    def number_of_edges(self) -> int:
        """Return the number of edges in the graph.

        Each undirected edge is counted once, including self-loops.
        """
        total = sum(len(nbrs) for nbrs in self._adj.values())
        if self._directed:
            return total
        # In an undirected graph each ordinary edge is stored twice
        # (u -> v and v -> u) but a self-loop is stored only once.
        self_loops = sum(1 for u, nbrs in self._adj.items() if u in nbrs)
        return (total + self_loops) // 2

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------
    def add_node(self, node: N) -> None:
        """Add ``node`` to the graph. Adding an existing node does nothing."""
        self._adj.setdefault(node, {})

    def add_edge(self, u: N, v: N, weight: float = 1.0) -> None:
        """Add an edge from ``u`` to ``v`` (both ways if undirected).

        Missing endpoints are added automatically. If the edge already
        exists, its weight is replaced.

        Args:
            u: Start node.
            v: End node.
            weight: Edge weight; must be a finite ``int`` or ``float``.

        Raises:
            TypeError: If ``weight`` is not a number.
            ValueError: If ``weight`` is NaN or infinite.
        """
        w = _validate_weight(weight)
        self.add_node(u)
        self.add_node(v)
        self._adj[u][v] = w
        if not self._directed:
            self._adj[v][u] = w

    def remove_node(self, node: N) -> None:
        """Remove ``node`` and every edge touching it.

        Raises:
            NodeNotFoundError: If ``node`` is not in the graph.
        """
        self._require(node)
        del self._adj[node]
        for nbrs in self._adj.values():
            nbrs.pop(node, None)

    def remove_edge(self, u: N, v: N) -> None:
        """Remove the edge from ``u`` to ``v`` (both ways if undirected).

        Raises:
            NodeNotFoundError: If either endpoint is not in the graph.
            EdgeNotFoundError: If the edge does not exist.
        """
        self._require(u)
        self._require(v)
        if v not in self._adj[u]:
            raise EdgeNotFoundError(u, v)
        del self._adj[u][v]
        if not self._directed:
            self._adj[v].pop(u, None)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def has_node(self, node: N) -> bool:
        """Return ``True`` if ``node`` is in the graph."""
        return node in self._adj

    def has_edge(self, u: N, v: N) -> bool:
        """Return ``True`` if there is an edge from ``u`` to ``v``.

        Unknown nodes simply give ``False`` rather than raising.
        """
        return u in self._adj and v in self._adj[u]

    def weight(self, u: N, v: N) -> float:
        """Return the weight of the edge from ``u`` to ``v``.

        Raises:
            NodeNotFoundError: If either endpoint is not in the graph.
            EdgeNotFoundError: If the edge does not exist.
        """
        self._require(u)
        self._require(v)
        try:
            return self._adj[u][v]
        except KeyError:
            raise EdgeNotFoundError(u, v) from None

    def nodes(self) -> list[N]:
        """Return a list of all nodes in insertion order."""
        return list(self._adj)

    def neighbors(self, node: N) -> Iterator[N]:
        """Iterate over the nodes reachable from ``node`` by a single edge.

        Raises:
            NodeNotFoundError: If ``node`` is not in the graph.
        """
        self._require(node)
        return iter(self._adj[node])

    def neighbor_items(self, node: N) -> Iterator[tuple[N, float]]:
        """Iterate over ``(neighbour, weight)`` pairs for ``node``.

        Raises:
            NodeNotFoundError: If ``node`` is not in the graph.
        """
        self._require(node)
        return iter(self._adj[node].items())

    def edges(self) -> Iterator[tuple[N, N, float]]:
        """Iterate over edges as ``(u, v, weight)`` triples.

        In an undirected graph every edge is reported exactly once.
        """
        if self._directed:
            for u, nbrs in self._adj.items():
                for v, w in nbrs.items():
                    yield u, v, w
            return
        done: set[N] = set()
        for u, nbrs in self._adj.items():
            for v, w in nbrs.items():
                if v not in done:
                    yield u, v, w
            done.add(u)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _require(self, node: N) -> None:
        """Raise :class:`NodeNotFoundError` if ``node`` is missing."""
        if node not in self._adj:
            raise NodeNotFoundError(node)
