"""Exception hierarchy for :mod:`graphkit`.

Every exception raised deliberately by the library derives from
:class:`GraphError`, so callers can catch all library errors with a single
``except GraphError`` clause while still being able to handle specific
failures individually.
"""

from __future__ import annotations

from collections.abc import Hashable


class GraphError(Exception):
    """Base class for all graphkit errors."""


class NodeNotFoundError(GraphError):
    """Raised when an operation refers to a node that is not in the graph."""

    def __init__(self, node: Hashable) -> None:
        super().__init__(f"node {node!r} is not in the graph")
        self.node = node


class EdgeNotFoundError(GraphError):
    """Raised when an operation refers to an edge that is not in the graph."""

    def __init__(self, u: Hashable, v: Hashable) -> None:
        super().__init__(f"edge ({u!r}, {v!r}) is not in the graph")
        self.u = u
        self.v = v


class NegativeWeightError(GraphError):
    """Raised when an algorithm that requires non-negative weights finds one.

    Dijkstra's algorithm and A* are only correct when every edge weight is
    non-negative; use Bellman-Ford for graphs with negative weights.
    """

    def __init__(self, u: Hashable, v: Hashable, weight: float) -> None:
        super().__init__(
            f"edge ({u!r}, {v!r}) has negative weight {weight!r}; "
            "use bellman_ford() for graphs with negative weights"
        )
        self.u = u
        self.v = v
        self.weight = weight


class NegativeCycleError(GraphError):
    """Raised when a negative-weight cycle is reachable from the source.

    With such a cycle, shortest-path distances are undefined, because going
    round the cycle again always makes the path cheaper.
    """


class GraphCycleError(GraphError):
    """Raised when an operation that requires an acyclic graph finds a cycle."""


class NoPathError(GraphError):
    """Raised when the target node is not reachable from the source node."""

    def __init__(self, source: Hashable, target: Hashable) -> None:
        super().__init__(f"no path from {source!r} to {target!r}")
        self.source = source
        self.target = target
