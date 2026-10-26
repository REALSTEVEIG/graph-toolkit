"""Command-line interface: ``graphkit`` / ``python -m graphkit``.

Run ``graphkit --help`` for the list of subcommands. Every subcommand
reads a graph from a ``.csv`` edge list or a ``.json`` file (see
:mod:`graphkit.io`).

Exit codes: ``0`` on success, ``1`` when the input or the request is bad
(missing file, malformed file, unknown node, no path, negative cycle, ...)
and ``2`` for invalid command-line usage (reported by :mod:`argparse`).
Errors are printed as a single ``graphkit: error: ...`` line on stderr,
never as a traceback.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import Any, TextIO

from . import __version__
from .exceptions import (
    GraphCycleError,
    GraphError,
    NegativeWeightError,
    NodeNotFoundError,
    NoPathError,
)
from .graph import Graph
from .io import load_graph
from .mst import prim_mst
from .shortest_paths import bellman_ford, reconstruct_path, shortest_path
from .traversal import bfs_shortest_path, connected_components, topological_sort

ALGORITHMS = ("dijkstra", "bellman-ford", "bfs")


class CLIError(Exception):
    """A user-facing error that should end the program with exit code 1."""


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _fmt(value: float) -> str:
    """Format a weight: whole numbers without decimals, others rounded."""
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.6f}".rstrip("0").rstrip(".")


def _load(path: str, directed: bool | None) -> Graph[Any]:
    return load_graph(path, directed=directed)


def _resolve_node(graph: Graph[Any], label: str) -> Any:
    """Map a command-line label to a node, accepting integer nodes from JSON."""
    if label in graph:
        return label
    try:
        number = int(label)
    except ValueError:
        number = None
    if number is not None and number in graph:
        return number
    raise NodeNotFoundError(label)


def _ordered(graph: Graph[Any], nodes: set[Any]) -> list[Any]:
    """Return ``nodes`` in the graph's insertion order."""
    return [node for node in graph if node in nodes]


# ----------------------------------------------------------------------
# Subcommands
# ----------------------------------------------------------------------
def cmd_shortest_path(args: argparse.Namespace, out: TextIO) -> None:
    graph = _load(args.file, True if args.directed else None)
    source = _resolve_node(graph, args.source)
    target = _resolve_node(graph, args.target)

    if args.algorithm == "bfs":
        path = bfs_shortest_path(graph, source, target)
        cost = None
    elif args.algorithm == "bellman-ford":
        dist, pred = bellman_ford(graph, source)
        if target not in dist:
            raise NoPathError(source, target)
        path, cost = reconstruct_path(pred, target), dist[target]
    else:
        try:
            path, cost = shortest_path(graph, source, target)
        except NegativeWeightError as exc:
            raise CLIError(
                f"edge ({exc.u!r}, {exc.v!r}) has negative weight {_fmt(exc.weight)}; "
                "dijkstra needs non-negative weights, use --algorithm bellman-ford"
            ) from None

    hops = len(path) - 1
    print(f"Shortest path from {source} to {target} ({args.algorithm}):", file=out)
    print("  " + " -> ".join(str(node) for node in path), file=out)
    if cost is None:
        print(f"  Edges: {hops} (weights ignored)", file=out)
    else:
        print(f"  Total weight: {_fmt(cost)}  ({hops} edges)", file=out)
        if len(path) > 2:
            print("  Legs:", file=out)
            for u, v in zip(path, path[1:], strict=False):
                print(f"    {u} -> {v}: {_fmt(graph.weight(u, v))}", file=out)


def cmd_mst(args: argparse.Namespace, out: TextIO) -> None:
    graph = _load(args.file, None)
    if graph.directed:
        raise CLIError("mst needs an undirected graph, but the file is directed")
    edges = prim_mst(graph)
    trees = len(connected_components(graph))
    total = sum(w for _, _, w in edges)
    kind = "tree" if trees == 1 else f"forest ({trees} trees)"
    print(
        f"Minimum spanning {kind}: {len(edges)} edges, total weight {_fmt(total)}",
        file=out,
    )
    width = max((len(f"{u} - {v}") for u, v, _ in edges), default=0)
    for u, v, w in edges:
        print(f"  {f'{u} - {v}':<{width}}  {_fmt(w):>8}", file=out)


def cmd_components(args: argparse.Namespace, out: TextIO) -> None:
    graph = _load(args.file, None)
    if graph.directed:
        raise CLIError("components needs an undirected graph, but the file is directed")
    components = connected_components(graph)
    noun = "component" if len(components) == 1 else "components"
    print(f"{len(components)} connected {noun}:", file=out)
    for i, comp in enumerate(components, start=1):
        names = ", ".join(str(node) for node in _ordered(graph, comp))
        print(f"  {i}. ({len(comp)} nodes) {names}", file=out)


def cmd_toposort(args: argparse.Namespace, out: TextIO) -> None:
    graph = _load(args.file, True)
    order = topological_sort(graph)
    print(f"Topological order ({len(order)} nodes):", file=out)
    width = len(str(len(order)))
    for i, node in enumerate(order, start=1):
        print(f"  {i:>{width}}. {node}", file=out)


def cmd_info(args: argparse.Namespace, out: TextIO) -> None:
    graph = _load(args.file, True if args.directed else None)
    weights = [w for _, _, w in graph.edges()]
    self_loops = sum(1 for u, v, _ in graph.edges() if u == v)
    isolated = [n for n in graph if not any(True for _ in graph.neighbors(n))]
    if graph.directed:
        has_incoming = {v for _, v, _ in graph.edges()}
        isolated = [n for n in isolated if n not in has_incoming]

    lines = [
        f"File:          {args.file}",
        f"Type:          {'directed' if graph.directed else 'undirected'}",
        f"Nodes:         {graph.number_of_nodes()}",
        f"Edges:         {graph.number_of_edges()}",
    ]
    if weights:
        lines += [
            f"Total weight:  {_fmt(sum(weights))}",
            f"Weight range:  {_fmt(min(weights))} to {_fmt(max(weights))}",
            f"Negative edges: {sum(1 for w in weights if w < 0)}",
        ]
    lines += [f"Self-loops:    {self_loops}", f"Isolated nodes: {len(isolated)}"]
    if graph.directed:
        try:
            topological_sort(graph)
            acyclic = "yes"
        except GraphCycleError:
            acyclic = "no"
        lines.append(f"Acyclic (DAG): {acyclic}")
    else:
        lines.append(f"Components:    {len(connected_components(graph))}")
    print("\n".join(lines), file=out)


# ----------------------------------------------------------------------
# Parser and entry point
# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="graphkit",
        description="Run graph algorithms on a CSV edge list or JSON graph file.",
        epilog="Example: graphkit shortest-path data/uk_roads.csv London Edinburgh",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    def add(name: str, help_text: str, func: Callable[..., None]) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text, description=help_text)
        p.add_argument("file", help="graph file (.csv edge list or .json)")
        p.set_defaults(func=func)
        return p

    sp = add("shortest-path", "Find the shortest path between two nodes.", cmd_shortest_path)
    sp.add_argument("source", help="start node")
    sp.add_argument("target", help="end node")
    sp.add_argument(
        "-a",
        "--algorithm",
        choices=ALGORITHMS,
        default="dijkstra",
        help="dijkstra (default, non-negative weights), bellman-ford "
        "(allows negative weights) or bfs (fewest edges, ignores weights)",
    )
    sp.add_argument(
        "-d", "--directed", action="store_true", help="treat edges as one-way"
    )

    add("mst", "Minimum spanning tree (Prim) of an undirected graph.", cmd_mst)
    add("components", "Connected components of an undirected graph.", cmd_components)
    add("toposort", "Topological order of a directed acyclic graph.", cmd_toposort)
    info = add("info", "Summary statistics for a graph file.", cmd_info)
    info.add_argument(
        "-d", "--directed", action="store_true", help="treat edges as one-way"
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the CLI and return its exit code.

    Bad command-line usage, ``--help`` and ``--version`` are handled by
    :mod:`argparse`, which raises :class:`SystemExit` (code 2 or 0).
    """
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    args = build_parser().parse_args(argv)
    try:
        args.func(args, out)
    except OSError as exc:
        filename = exc.filename if exc.filename is not None else args.file
        reason = exc.strerror or str(exc)
        print(f"graphkit: error: cannot read {filename!s}: {reason}", file=err)
        return 1
    except (GraphError, CLIError, ValueError) as exc:
        print(f"graphkit: error: {exc}", file=err)
        return 1
    return 0


def main_entry() -> None:
    """Console-script entry point: run :func:`main` and exit with its code."""
    sys.exit(main())
