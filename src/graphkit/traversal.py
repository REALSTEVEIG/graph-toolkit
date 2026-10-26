"""Unweighted traversals and structural algorithms.

All functions here ignore edge weights. Every one runs in O(V + E) time,
where V is the number of nodes and E the number of edges.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Hashable
from typing import TypeVar

from .exceptions import GraphCycleError, NodeNotFoundError, NoPathError
from .graph import Graph

N = TypeVar("N", bound=Hashable)


def _require(graph: Graph[N], node: N) -> None:
    if not graph.has_node(node):
        raise NodeNotFoundError(node)


def bfs(graph: Graph[N], source: N) -> list[N]:
    """Return nodes reachable from ``source`` in breadth-first order.

    Nodes are visited level by level: first ``source``, then all nodes one
    edge away, then all nodes two edges away, and so on.

    Raises:
        NodeNotFoundError: If ``source`` is not in the graph.
    """
    _require(graph, source)
    visited: set[N] = {source}
    order: list[N] = []
    queue: deque[N] = deque([source])
    while queue:
        node = queue.popleft()
        order.append(node)
        for nbr in graph.neighbors(node):
            if nbr not in visited:
                visited.add(nbr)
                queue.append(nbr)
    return order


def dfs(graph: Graph[N], source: N) -> list[N]:
    """Return nodes reachable from ``source`` in depth-first (pre-)order.

    Implemented iteratively with an explicit stack, so it cannot hit
    Python's recursion limit on deep graphs. Neighbours are pushed in
    reverse so that they are explored in insertion order, matching the
    order a recursive implementation would produce.

    Raises:
        NodeNotFoundError: If ``source`` is not in the graph.
    """
    _require(graph, source)
    visited: set[N] = set()
    order: list[N] = []
    stack: list[N] = [source]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        order.append(node)
        for nbr in reversed(list(graph.neighbors(node))):
            if nbr not in visited:
                stack.append(nbr)
    return order


def bfs_shortest_path(graph: Graph[N], source: N, target: N) -> list[N]:
    """Return a path from ``source`` to ``target`` with the fewest edges.

    Weights are ignored; each edge counts as one step.

    Raises:
        NodeNotFoundError: If ``source`` or ``target`` is not in the graph.
        NoPathError: If ``target`` cannot be reached from ``source``.
    """
    _require(graph, source)
    _require(graph, target)
    parent: dict[N, N | None] = {source: None}
    queue: deque[N] = deque([source])
    while queue:
        node = queue.popleft()
        if node == target:
            break
        for nbr in graph.neighbors(node):
            if nbr not in parent:
                parent[nbr] = node
                queue.append(nbr)
    if target not in parent:
        raise NoPathError(source, target)

    path: list[N] = []
    current: N | None = target
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path


def topological_sort(graph: Graph[N]) -> list[N]:
    """Return the nodes of a directed acyclic graph in topological order.

    Uses Kahn's algorithm: repeatedly remove a node with no incoming edges.
    If nodes remain that always have an incoming edge, they lie on a cycle.

    Raises:
        ValueError: If the graph is undirected.
        GraphCycleError: If the graph contains a cycle (including a self-loop).
    """
    if not graph.directed:
        raise ValueError("topological sort requires a directed graph")

    in_degree: dict[N, int] = {node: 0 for node in graph}
    for _, v, _ in graph.edges():
        in_degree[v] += 1

    queue: deque[N] = deque(node for node, deg in in_degree.items() if deg == 0)
    order: list[N] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nbr in graph.neighbors(node):
            in_degree[nbr] -= 1
            if in_degree[nbr] == 0:
                queue.append(nbr)

    if len(order) != len(graph):
        remaining = [node for node, deg in in_degree.items() if deg > 0]
        raise GraphCycleError(
            f"graph contains a cycle; nodes on or after a cycle: {remaining!r}"
        )
    return order


def connected_components(graph: Graph[N]) -> list[set[N]]:
    """Return the connected components of an undirected graph.

    Each component is a set of nodes that can all reach each other. An
    isolated node forms a component on its own. Components are returned in
    the order their first node was added to the graph.

    Raises:
        ValueError: If the graph is directed (connectivity is ambiguous
            there: weak vs. strong components).
    """
    if graph.directed:
        raise ValueError("connected_components requires an undirected graph")
    seen: set[N] = set()
    components: list[set[N]] = []
    for node in graph:
        if node not in seen:
            component = set(bfs(graph, node))
            seen |= component
            components.append(component)
    return components
