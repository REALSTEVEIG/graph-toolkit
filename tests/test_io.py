"""Tests for loading and saving graphs as CSV and JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from graphkit import (
    Graph,
    GraphFormatError,
    graph_from_dict,
    graph_to_dict,
    load_graph,
    read_csv,
    read_json,
    save_graph,
    write_csv,
    write_json,
)

DATA = Path(__file__).resolve().parent.parent / "data"


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _edge_set(g: Graph[object]) -> set[tuple[object, object, float]]:
    return set(g.edges())


# --- CSV reading ---------------------------------------------------------
def test_read_csv_basic(tmp_path: Path) -> None:
    p = _write(tmp_path / "g.csv", "source,target,weight\na,b,2\nb,c,3.5\n")
    g = read_csv(p)
    assert not g.directed
    assert g.nodes() == ["a", "b", "c"]
    assert g.weight("b", "a") == 2.0
    assert g.weight("c", "b") == 3.5


def test_read_csv_directed(tmp_path: Path) -> None:
    p = _write(tmp_path / "g.csv", "source,target,weight\na,b,2\n")
    g = read_csv(p, directed=True)
    assert g.directed
    assert g.has_edge("a", "b")
    assert not g.has_edge("b", "a")


def test_read_csv_two_columns_defaults_weight(tmp_path: Path) -> None:
    p = _write(tmp_path / "g.csv", "source,target\na,b\n")
    assert read_csv(p).weight("a", "b") == 1.0


def test_read_csv_empty_weight_defaults_to_one(tmp_path: Path) -> None:
    p = _write(tmp_path / "g.csv", "source,target,weight\na,b,\n")
    assert read_csv(p).weight("a", "b") == 1.0


def test_read_csv_comments_blank_lines_whitespace_and_bom(tmp_path: Path) -> None:
    text = "\ufeff# a comment\n\n Source , Target , Weight \n\n  a , b , 4 \n# x,y,1\n"
    g = read_csv(_write(tmp_path / "g.csv", text))
    assert list(g.edges()) == [("a", "b", 4.0)]


def test_read_csv_isolated_node_and_quoted_labels(tmp_path: Path) -> None:
    text = 'source,target,weight\n"Stoke-on-Trent, Staffs",Leek,20\nLonely,,\n'
    g = read_csv(_write(tmp_path / "g.csv", text))
    assert g.nodes() == ["Stoke-on-Trent, Staffs", "Leek", "Lonely"]
    assert g.number_of_edges() == 1


def test_read_csv_negative_weight_allowed(tmp_path: Path) -> None:
    g = read_csv(_write(tmp_path / "g.csv", "source,target,weight\na,b,-3\n"), directed=True)
    assert g.weight("a", "b") == -3.0


@pytest.mark.parametrize(
    ("text", "message", "line"),
    [
        ("", "file is empty", None),
        ("# only a comment\n", "file is empty", None),
        ("from,to,cost\na,b,1\n", "header must be", 1),
        ("source,target,weight\na,b\n", "expected 3 columns, got 2", 2),
        ("source,target,weight\na,b,1,9\n", "expected 3 columns, got 4", 2),
        ("source,target,weight\na,b,heavy\n", "not a number", 2),
        ("source,target,weight\na,b,nan\n", "finite", 2),
        ("source,target,weight\na,b,inf\n", "finite", 2),
        ("source,target,weight\n,b,1\n", "source node is empty", 2),
        ("source,target,weight\na,,5\n", "node-only row", 2),
        ("source,target,weight\na,b,1\n\nb,a,2\n", "duplicate edge", 4),
    ],
)
def test_read_csv_errors(tmp_path: Path, text: str, message: str, line: int | None) -> None:
    p = _write(tmp_path / "bad.csv", text)
    with pytest.raises(GraphFormatError, match=message) as info:
        read_csv(p)
    assert info.value.line == line
    assert info.value.path == str(p)
    assert str(p) in str(info.value)


def test_read_csv_duplicate_is_fine_when_directed(tmp_path: Path) -> None:
    p = _write(tmp_path / "g.csv", "source,target,weight\na,b,1\nb,a,2\n")
    g = read_csv(p, directed=True)
    assert g.weight("a", "b") == 1.0
    assert g.weight("b", "a") == 2.0


def test_read_csv_not_utf8(tmp_path: Path) -> None:
    p = tmp_path / "bin.csv"
    p.write_bytes(b"source,target\n\xff\xfe,\x80\n")
    with pytest.raises(GraphFormatError, match="UTF-8"):
        read_csv(p)


def test_read_csv_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_csv(tmp_path / "missing.csv")


# --- CSV writing ---------------------------------------------------------
def test_csv_round_trip(tmp_path: Path) -> None:
    g: Graph[str] = Graph()
    g.add_edge("a", "b", 2)
    g.add_edge("b", "c", 0.25)
    g.add_edge("Hull, East Yorkshire", "a", 7)
    g.add_node("solo")
    p = tmp_path / "out.csv"
    write_csv(g, p)
    text = p.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "source,target,weight"
    assert "a,b,2\n" in text  # whole numbers have no ".0"
    back = read_csv(p)
    assert set(back.nodes()) == set(g.nodes())
    assert {frozenset((u, v)): w for u, v, w in back.edges()} == {
        frozenset((u, v)): w for u, v, w in g.edges()
    }


def test_csv_round_trip_directed(tmp_path: Path) -> None:
    g: Graph[str] = Graph(directed=True)
    g.add_edge("a", "b", 1)
    g.add_edge("b", "a", 5)
    p = tmp_path / "out.csv"
    write_csv(g, p)
    assert _edge_set(read_csv(p, directed=True)) == _edge_set(g)


@pytest.mark.parametrize("label", ["", " padded", "two\nlines"])
def test_write_csv_rejects_unstorable_labels(tmp_path: Path, label: str) -> None:
    g: Graph[str] = Graph()
    g.add_edge(label, "b")
    with pytest.raises(ValueError, match="cannot be stored"):
        write_csv(g, tmp_path / "out.csv")


# --- JSON ----------------------------------------------------------------
def test_read_json_full(tmp_path: Path) -> None:
    doc = {
        "directed": True,
        "nodes": ["iso"],
        "edges": [{"source": "a", "target": "b", "weight": 2.5}, {"source": 1, "target": 2}],
    }
    g = read_json(_write(tmp_path / "g.json", json.dumps(doc)))
    assert g.directed
    assert g.nodes() == ["iso", "a", "b", 1, 2]
    assert g.weight("a", "b") == 2.5
    assert g.weight(1, 2) == 1.0


def test_read_json_defaults_and_override(tmp_path: Path) -> None:
    p = _write(tmp_path / "g.json", '{"edges": [{"source": "a", "target": "b"}]}')
    assert not read_json(p).directed
    assert read_json(p, directed=True).directed


@pytest.mark.parametrize(
    ("doc", "message"),
    [
        ("[1, 2]", "top level must be a JSON object"),
        ('{"directed": "yes"}', "'directed' must be true or false"),
        ('{"nodes": "a"}', "'nodes' must be a list"),
        ('{"edges": {}}', "'edges' must be a list"),
        ('{"nodes": [1.5]}', r"nodes\[0\] must be a string or integer"),
        ('{"nodes": [true]}', r"nodes\[0\] must be a string or integer"),
        ('{"nodes": ["  "]}', "must not be empty"),
        ('{"edges": [["a", "b"]]}', r"edges\[0\] must be an object"),
        ('{"edges": [{"source": "a"}]}', "needs both 'source' and 'target'"),
        ('{"edges": [{"source": "a", "target": "b", "w": 1}]}', "unknown key"),
        ('{"edges": [{"source": "a", "target": "b", "weight": "x"}]}', "must be a number"),
        ('{"edges": [{"source": "a", "target": "b", "weight": true}]}', "must be a number"),
        ('{"edges": [{"source": "a", "target": "b", "weight": NaN}]}', "finite"),
        (
            '{"edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}]}',
            "duplicate edge",
        ),
        ('{"vertices": []}', "unknown key"),
        ("{not json", "invalid JSON"),
    ],
)
def test_read_json_errors(tmp_path: Path, doc: str, message: str) -> None:
    p = _write(tmp_path / "bad.json", doc)
    with pytest.raises(GraphFormatError, match=message):
        read_json(p)


def test_json_round_trip(tmp_path: Path) -> None:
    g: Graph[object] = Graph(directed=True)
    g.add_edge("a", "b", 3)
    g.add_edge(1, "a", -0.5)
    g.add_node("solo")
    p = tmp_path / "g.json"
    write_json(g, p)
    back = read_json(p)
    assert back.directed
    assert back.nodes() == g.nodes()
    assert _edge_set(back) == _edge_set(g)
    assert json.loads(p.read_text())["edges"][0]["weight"] == 3  # int, not 3.0


def test_graph_to_dict_rejects_unsupported_nodes() -> None:
    g: Graph[object] = Graph()
    g.add_edge((0, 0), (0, 1))
    with pytest.raises(TypeError):
        graph_to_dict(g)


def test_graph_from_dict_direct() -> None:
    g = graph_from_dict({"edges": [{"source": "x", "target": "y", "weight": 4}]})
    assert g.weight("y", "x") == 4.0


# --- dispatch ------------------------------------------------------------
def test_load_and_save_dispatch_on_extension(tmp_path: Path) -> None:
    g: Graph[str] = Graph()
    g.add_edge("a", "b", 2)
    for name in ("g.csv", "g.JSON"):
        save_graph(g, tmp_path / name)
        assert _edge_set(load_graph(tmp_path / name)) == _edge_set(g)


def test_load_csv_directed_flag(tmp_path: Path) -> None:
    p = _write(tmp_path / "g.csv", "source,target\na,b\n")
    assert load_graph(p, directed=True).directed
    assert not load_graph(p).directed


def test_unsupported_extension(tmp_path: Path) -> None:
    g: Graph[str] = Graph()
    with pytest.raises(GraphFormatError, match="unsupported file type"):
        load_graph(_write(tmp_path / "g.txt", "x"))
    with pytest.raises(GraphFormatError, match="unsupported file type"):
        save_graph(g, tmp_path / "g.xml")


# --- bundled data ----------------------------------------------------------
def test_bundled_uk_roads() -> None:
    g = read_csv(DATA / "uk_roads.csv")
    assert 15 <= len(g) <= 25
    assert g.weight("London", "Cambridge") == 98.0
    assert all(w > 0 for _, _, w in g.edges())


def test_bundled_tasks_is_directed_dag() -> None:
    from graphkit import topological_sort

    g = read_csv(DATA / "project_tasks.csv", directed=True)
    order = topological_sort(g)
    assert order[0] == "gather-requirements"
    assert order[-1] == "announce-launch"


def test_bundled_json() -> None:
    g = read_json(DATA / "lake_district_ev.json")
    assert g.directed
    assert any(w < 0 for _, _, w in g.edges())
