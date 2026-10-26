"""Reading and writing graphs as CSV edge lists or JSON documents.

CSV format
----------
A header row followed by one edge per row::

    source,target,weight
    London,Cambridge,98
    Cambridge,Norwich,102

* The header must be ``source,target`` or ``source,target,weight``.
* An empty weight (or a missing weight column) means ``1``.
* A row with a source but an empty target declares an isolated node.
* Blank lines and lines starting with ``#`` are ignored.
* Node labels are always read as strings.

CSV has no place to record whether a graph is directed, so the caller
chooses with the ``directed`` argument.

JSON format
-----------
::

    {
      "directed": false,
      "nodes": ["Belfast", "Derry"],
      "edges": [
        {"source": "Belfast", "target": "Derry", "weight": 117}
      ]
    }

* ``directed`` is optional and defaults to ``false``.
* ``nodes`` is optional; it is only needed for isolated nodes.
* ``weight`` is optional and defaults to ``1``.
* Node labels must be strings or integers.

All content problems raise :class:`GraphFormatError`, which says which file
and (for CSV) which line is wrong. Operating-system problems such as a
missing file raise the usual :class:`OSError` subclasses.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Hashable, Iterator
from os import PathLike
from pathlib import Path
from typing import Any, TypeAlias

from .exceptions import GraphError
from .graph import Graph

StrPath: TypeAlias = str | PathLike[str]
JsonNode: TypeAlias = str | int

_CSV_HEADERS = (("source", "target"), ("source", "target", "weight"))


class GraphFormatError(GraphError):
    """Raised when a graph file is malformed.

    Attributes:
        path: The file that could not be read.
        line: 1-based line number of the problem, if known.
    """

    def __init__(self, path: StrPath, message: str, line: int | None = None) -> None:
        location = f"{path}:{line}" if line is not None else f"{path}"
        super().__init__(f"{location}: {message}")
        self.path = str(path)
        self.line = line


# ----------------------------------------------------------------------
# Shared validation
# ----------------------------------------------------------------------
def _parse_weight(text: str) -> float:
    """Parse a CSV weight cell; an empty cell means 1."""
    text = text.strip()
    if not text:
        return 1.0
    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"weight {text!r} is not a number") from None
    if not math.isfinite(value):
        raise ValueError(f"weight {text!r} must be a finite number")
    return value


def _add_unique_edge(
    graph: Graph[Any], u: Hashable, v: Hashable, weight: float
) -> None:
    """Add an edge, rejecting duplicates (which would silently overwrite)."""
    if graph.has_edge(u, v):
        raise ValueError(f"duplicate edge {u!r} -> {v!r}")
    graph.add_edge(u, v, weight)


# ----------------------------------------------------------------------
# CSV
# ----------------------------------------------------------------------
def read_csv(path: StrPath, *, directed: bool = False) -> Graph[str]:
    """Load a graph from a CSV edge list.

    Args:
        path: File to read (UTF-8).
        directed: Build a directed graph instead of an undirected one.

    Returns:
        The graph, with nodes in the order they first appear.

    Raises:
        GraphFormatError: If the header, a node label or a weight is
            invalid, a row has the wrong number of columns, or an edge is
            listed twice.
        OSError: If the file cannot be opened.
    """
    graph: Graph[str] = Graph(directed=directed)
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rows = _content_rows(csv.reader(fh))
            try:
                header_line, header = next(rows)
            except StopIteration:
                raise GraphFormatError(path, "file is empty (expected a header)") from None
            columns = tuple(cell.strip().lower() for cell in header)
            if columns not in _CSV_HEADERS:
                raise GraphFormatError(
                    path,
                    f"header must be 'source,target' or 'source,target,weight', "
                    f"got {','.join(header)!r}",
                    header_line,
                )
            for line, row in rows:
                if len(row) != len(columns):
                    raise GraphFormatError(
                        path,
                        f"expected {len(columns)} columns, got {len(row)}",
                        line,
                    )
                source = row[0].strip()
                target = row[1].strip()
                weight_cell = row[2] if len(row) == 3 else ""
                if not source:
                    raise GraphFormatError(path, "source node is empty", line)
                try:
                    if not target:
                        if weight_cell.strip():
                            raise ValueError("a node-only row cannot have a weight")
                        graph.add_node(source)
                    else:
                        _add_unique_edge(graph, source, target, _parse_weight(weight_cell))
                except ValueError as err:
                    raise GraphFormatError(path, str(err), line) from None
    except UnicodeDecodeError:
        raise GraphFormatError(path, "file is not valid UTF-8 text") from None
    except csv.Error as err:
        raise GraphFormatError(path, f"invalid CSV: {err}") from None
    return graph


def _content_rows(reader: Any) -> Iterator[tuple[int, list[str]]]:
    """Yield ``(line_number, row)``, skipping blank and ``#`` comment rows."""
    for row in reader:
        line: int = reader.line_num
        if not row or all(not cell.strip() for cell in row):
            continue
        if row[0].lstrip().startswith("#"):
            continue
        yield line, row


def write_csv(graph: Graph[Any], path: StrPath) -> None:
    """Save a graph as a CSV edge list with a ``source,target,weight`` header.

    Isolated nodes are written as rows with an empty target. Weights that
    are whole numbers are written without a decimal point. Whether the
    graph is directed is *not* stored; pass ``directed`` when reading back.

    Raises:
        ValueError: If a node label contains a newline or is empty when
            written, since it could not be read back unchanged.
        OSError: If the file cannot be written.
    """
    rows: list[list[str]] = []
    connected: set[Any] = set()
    for u, v, w in graph.edges():
        rows.append([_csv_label(u), _csv_label(v), _format_weight(w)])
        connected.update((u, v))
    for node in graph:
        if node not in connected:
            rows.append([_csv_label(node), "", ""])
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["source", "target", "weight"])
        writer.writerows(rows)


def _csv_label(node: Any) -> str:
    text = str(node)
    if not text.strip() or text != text.strip() or "\n" in text or "\r" in text:
        raise ValueError(f"node {node!r} cannot be stored in a CSV edge list")
    return text


def _format_weight(weight: float) -> str:
    return str(int(weight)) if weight.is_integer() else repr(weight)


# ----------------------------------------------------------------------
# JSON
# ----------------------------------------------------------------------
def read_json(path: StrPath, *, directed: bool | None = None) -> Graph[JsonNode]:
    """Load a graph from a JSON document (see the module docstring).

    Args:
        path: File to read (UTF-8).
        directed: Override the file's ``directed`` value. ``None`` (the
            default) uses the value stored in the file.

    Raises:
        GraphFormatError: If the JSON is invalid or does not match the
            expected structure.
        OSError: If the file cannot be opened.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except UnicodeDecodeError:
        raise GraphFormatError(path, "file is not valid UTF-8 text") from None
    except json.JSONDecodeError as err:
        raise GraphFormatError(path, f"invalid JSON: {err.msg}", err.lineno) from None
    try:
        return graph_from_dict(data, directed=directed)
    except (TypeError, ValueError) as err:
        raise GraphFormatError(path, str(err)) from None


def graph_from_dict(
    data: Any, *, directed: bool | None = None
) -> Graph[JsonNode]:
    """Build a graph from the parsed JSON structure.

    Raises:
        TypeError: If a value has the wrong type.
        ValueError: If a value is invalid or an edge is duplicated.
    """
    if not isinstance(data, dict):
        raise TypeError("top level must be a JSON object")
    unknown = set(data) - {"directed", "nodes", "edges"}
    if unknown:
        raise ValueError(f"unknown key(s): {', '.join(sorted(unknown))}")

    stored = data.get("directed", False)
    if not isinstance(stored, bool):
        raise TypeError("'directed' must be true or false")
    graph: Graph[JsonNode] = Graph(directed=stored if directed is None else directed)

    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        raise TypeError("'nodes' must be a list")
    for i, node in enumerate(nodes):
        graph.add_node(_json_node(node, f"nodes[{i}]"))

    edges = data.get("edges", [])
    if not isinstance(edges, list):
        raise TypeError("'edges' must be a list")
    for i, edge in enumerate(edges):
        where = f"edges[{i}]"
        if not isinstance(edge, dict):
            raise TypeError(f"{where} must be an object with 'source' and 'target'")
        extra = set(edge) - {"source", "target", "weight"}
        if extra:
            raise ValueError(f"{where} has unknown key(s): {', '.join(sorted(extra))}")
        if "source" not in edge or "target" not in edge:
            raise ValueError(f"{where} needs both 'source' and 'target'")
        u = _json_node(edge["source"], f"{where}.source")
        v = _json_node(edge["target"], f"{where}.target")
        weight = edge.get("weight", 1)
        try:
            _add_unique_edge(graph, u, v, weight)
        except (TypeError, ValueError) as err:
            raise type(err)(f"{where}: {err}") from None
    return graph


def _json_node(value: Any, where: str) -> JsonNode:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise TypeError(f"{where} must be a string or integer, got {value!r}")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"{where} must not be empty")
    return value


def graph_to_dict(graph: Graph[Any]) -> dict[str, Any]:
    """Return a JSON-ready dictionary describing ``graph``.

    Raises:
        TypeError: If a node is not a string or integer.
    """
    for node in graph:
        _json_node(node, f"node {node!r}")
    edges = [
        {"source": u, "target": v, "weight": int(w) if w.is_integer() else w}
        for u, v, w in graph.edges()
    ]
    return {"directed": graph.directed, "nodes": graph.nodes(), "edges": edges}


def write_json(graph: Graph[Any], path: StrPath, *, indent: int | None = 2) -> None:
    """Save a graph as JSON, including whether it is directed and every node.

    Raises:
        TypeError: If a node is not a string or integer.
        OSError: If the file cannot be written.
    """
    text = json.dumps(graph_to_dict(graph), indent=indent, ensure_ascii=False)
    Path(path).write_text(text + "\n", encoding="utf-8")


# ----------------------------------------------------------------------
# Format dispatch
# ----------------------------------------------------------------------
def load_graph(path: StrPath, *, directed: bool | None = None) -> Graph[Any]:
    """Load a graph, choosing CSV or JSON from the file extension.

    Args:
        path: A ``.csv`` or ``.json`` file.
        directed: For CSV, ``None`` means undirected. For JSON, ``None``
            means use the value stored in the file.

    Raises:
        GraphFormatError: If the extension is unknown or the content is bad.
        OSError: If the file cannot be opened.
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return read_csv(path, directed=bool(directed))
    if suffix == ".json":
        return read_json(path, directed=directed)
    raise GraphFormatError(path, "unsupported file type (use .csv or .json)")


def save_graph(graph: Graph[Any], path: StrPath) -> None:
    """Save a graph as CSV or JSON, chosen from the file extension.

    Raises:
        GraphFormatError: If the extension is not ``.csv`` or ``.json``.
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        write_csv(graph, path)
    elif suffix == ".json":
        write_json(graph, path)
    else:
        raise GraphFormatError(path, "unsupported file type (use .csv or .json)")
