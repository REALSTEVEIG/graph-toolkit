"""End-to-end tests for the ``graphkit`` command-line interface.

Most tests call :func:`graphkit.cli.main` in-process with captured output;
a few run ``python -m graphkit`` in a subprocess to check the real entry
point, exit codes and that errors never show a traceback.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from graphkit.cli import main

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ROADS = str(DATA / "uk_roads.csv")
TASKS = str(DATA / "project_tasks.csv")
EV = str(DATA / "lake_district_ev.json")


def run(*argv: str) -> tuple[int, str, str]:
    """Run the CLI in-process and return ``(exit_code, stdout, stderr)``."""
    out, err = io.StringIO(), io.StringIO()
    code = main(list(argv), stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


def run_subprocess(*argv: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(ROOT / "src"), env.get("PYTHONPATH")) if p
    )
    return subprocess.run(
        [sys.executable, "-m", "graphkit", *argv],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        timeout=60,
    )


def assert_clean_error(code: int, out: str, err: str, fragment: str) -> None:
    assert code == 1
    assert out == ""
    assert err.startswith("graphkit: error: ")
    assert fragment in err
    assert "Traceback" not in err


# --- shortest-path ---------------------------------------------------------
def test_shortest_path_dijkstra_on_bundled_roads() -> None:
    code, out, err = run("shortest-path", ROADS, "London", "Edinburgh")
    assert code == 0, err
    expected = "London -> Cambridge -> Nottingham -> Sheffield -> Leeds -> Newcastle -> Edinburgh"
    assert expected in out
    assert "Total weight: 689" in out
    assert "Newcastle -> Edinburgh: 190" in out


def test_shortest_path_bellman_ford_matches_dijkstra() -> None:
    _, dij, _ = run("shortest-path", ROADS, "Plymouth", "Aberdeen")
    code, bf, _ = run("shortest-path", ROADS, "Plymouth", "Aberdeen", "-a", "bellman-ford")
    assert code == 0
    assert dij.splitlines()[1:] == bf.splitlines()[1:]


def test_shortest_path_bfs_counts_edges() -> None:
    code, out, _ = run("shortest-path", ROADS, "London", "Glasgow", "--algorithm", "bfs")
    assert code == 0
    assert "(bfs)" in out
    assert "weights ignored" in out
    assert "Total weight" not in out


def test_shortest_path_same_node() -> None:
    code, out, _ = run("shortest-path", ROADS, "York", "York")
    assert code == 0
    assert "Total weight: 0  (0 edges)" in out


def test_shortest_path_directed_flag(tmp_path: Path) -> None:
    p = tmp_path / "oneway.csv"
    p.write_text("source,target,weight\na,b,1\n", encoding="utf-8")
    assert run("shortest-path", str(p), "b", "a")[0] == 0
    code, out, err = run("shortest-path", str(p), "b", "a", "--directed")
    assert_clean_error(code, out, err, "no path from 'b' to 'a'")


def test_shortest_path_negative_weights_with_bellman_ford() -> None:
    code, out, _ = run(
        "shortest-path", EV, "Kendal", "Patterdale", "--algorithm", "bellman-ford"
    )
    assert code == 0
    assert "Kendal -> Windermere -> Kirkstone Pass -> Patterdale" in out
    assert "Total weight: 5" in out


def test_shortest_path_integer_nodes_from_json(tmp_path: Path) -> None:
    p = tmp_path / "ints.json"
    p.write_text('{"edges": [{"source": 1, "target": 2, "weight": 3}]}', encoding="utf-8")
    code, out, _ = run("shortest-path", str(p), "1", "2")
    assert code == 0
    assert "1 -> 2" in out


# --- shortest-path error paths -------------------------------------------
def test_error_missing_node() -> None:
    assert_clean_error(
        *run("shortest-path", ROADS, "London", "Paris"), "node 'Paris' is not in the graph"
    )


def test_error_no_path() -> None:
    assert_clean_error(
        *run("shortest-path", ROADS, "London", "Belfast"), "no path from 'London' to 'Belfast'"
    )


@pytest.mark.parametrize("algorithm", ["bellman-ford", "bfs"])
def test_error_no_path_other_algorithms(algorithm: str) -> None:
    assert_clean_error(
        *run("shortest-path", ROADS, "Derry", "Cardiff", "-a", algorithm), "no path"
    )


def test_error_negative_weight_with_dijkstra() -> None:
    assert_clean_error(
        *run("shortest-path", EV, "Kendal", "Patterdale"), "use --algorithm bellman-ford"
    )


def test_error_negative_cycle(tmp_path: Path) -> None:
    p = tmp_path / "cycle.csv"
    p.write_text("source,target,weight\na,b,1\nb,c,-3\nc,a,1\n", encoding="utf-8")
    assert_clean_error(
        *run("shortest-path", str(p), "a", "c", "-a", "bellman-ford", "--directed"),
        "negative cycle",
    )


# --- mst / components / toposort / info ----------------------------------
def test_mst_on_bundled_roads() -> None:
    code, out, _ = run("mst", ROADS)
    assert code == 0
    assert out.startswith("Minimum spanning forest (2 trees): 22 edges, total weight 2,109")
    assert "Belfast - Derry" in out


def test_mst_single_tree(tmp_path: Path) -> None:
    p = tmp_path / "tri.csv"
    p.write_text("source,target,weight\na,b,1\nb,c,2\na,c,5\n", encoding="utf-8")
    code, out, _ = run("mst", str(p))
    assert code == 0
    assert out.startswith("Minimum spanning tree: 2 edges, total weight 3")


def test_mst_rejects_directed_json() -> None:
    assert_clean_error(*run("mst", EV), "undirected")


def test_components_on_bundled_roads() -> None:
    code, out, _ = run("components", ROADS)
    assert code == 0
    assert out.startswith("2 connected components:")
    assert "2. (2 nodes) Belfast, Derry" in out


def test_components_rejects_directed_json() -> None:
    assert_clean_error(*run("components", EV), "undirected")


def test_toposort_on_bundled_tasks() -> None:
    code, out, _ = run("toposort", TASKS)
    assert code == 0
    lines = [line.split(". ", 1)[1] for line in out.splitlines()[1:]]
    assert lines[0] == "gather-requirements"
    assert lines[-1] == "announce-launch"
    assert lines.index("build-api") < lines.index("build-frontend")
    assert lines.index("set-up-ci") < lines.index("write-ui-tests")


def test_toposort_cycle_error(tmp_path: Path) -> None:
    p = tmp_path / "cycle.csv"
    p.write_text("source,target\na,b\nb,a\n", encoding="utf-8")
    assert_clean_error(*run("toposort", str(p)), "cycle")


def test_info_undirected() -> None:
    code, out, _ = run("info", ROADS)
    assert code == 0
    assert "Type:          undirected" in out
    assert "Nodes:         24" in out
    assert "Edges:         35" in out
    assert "Components:    2" in out


def test_info_directed_tasks() -> None:
    code, out, _ = run("info", TASKS, "--directed")
    assert code == 0
    assert "Type:          directed" in out
    assert "Acyclic (DAG): yes" in out


def test_info_json_with_isolated_node(tmp_path: Path) -> None:
    p = tmp_path / "g.json"
    p.write_text('{"directed": true, "nodes": ["z"], "edges": [{"source": "a", "target": "b"}]}')
    code, out, _ = run("info", str(p))
    assert code == 0
    assert "Isolated nodes: 1" in out


def test_info_empty_graph(tmp_path: Path) -> None:
    p = tmp_path / "empty.csv"
    p.write_text("source,target,weight\n", encoding="utf-8")
    code, out, _ = run("info", str(p))
    assert code == 0
    assert "Nodes:         0" in out


# --- file errors -----------------------------------------------------------
def test_error_missing_file(tmp_path: Path) -> None:
    assert_clean_error(*run("info", str(tmp_path / "nope.csv")), "No such file")


def test_error_directory_instead_of_file(tmp_path: Path) -> None:
    d = tmp_path / "dir.csv"
    d.mkdir()
    assert_clean_error(*run("info", str(d)), "cannot read")


def test_error_bad_csv(tmp_path: Path) -> None:
    p = tmp_path / "bad.csv"
    p.write_text("source,target,weight\na,b,heavy\n", encoding="utf-8")
    assert_clean_error(*run("mst", str(p)), "bad.csv:2: weight 'heavy' is not a number")


def test_error_bad_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{oops", encoding="utf-8")
    assert_clean_error(*run("info", str(p)), "invalid JSON")


def test_error_unsupported_extension(tmp_path: Path) -> None:
    p = tmp_path / "graph.txt"
    p.write_text("a b", encoding="utf-8")
    assert_clean_error(*run("info", str(p)), "unsupported file type")


# --- argparse usage --------------------------------------------------------
def test_usage_errors_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code == 2
    with pytest.raises(SystemExit) as info:
        main(["shortest-path", ROADS, "London", "York", "-a", "floyd"])
    assert info.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_help_and_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--help"])
    assert info.value.code == 0
    out = capsys.readouterr().out
    for command in ("shortest-path", "mst", "components", "toposort", "info"):
        assert command in out
    with pytest.raises(SystemExit):
        main(["--version"])
    assert "graphkit 0.1.0" in capsys.readouterr().out


# --- real subprocess -------------------------------------------------------
def test_subprocess_success() -> None:
    result = run_subprocess("shortest-path", "data/uk_roads.csv", "London", "Edinburgh")
    assert result.returncode == 0, result.stderr
    assert "Total weight: 689" in result.stdout
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("argv", "fragment"),
    [
        (["shortest-path", "data/uk_roads.csv", "London", "Atlantis"], "not in the graph"),
        (["shortest-path", "data/uk_roads.csv", "London", "Derry"], "no path"),
        (["info", "data/does-not-exist.csv"], "No such file"),
        (["toposort", "data/lake_district_ev.json"], "cycle"),
    ],
)
def test_subprocess_errors_have_no_traceback(argv: list[str], fragment: str) -> None:
    result = run_subprocess(*argv)
    assert result.returncode == 1
    assert result.stdout == ""
    assert fragment in result.stderr
    assert "Traceback" not in result.stderr


def test_subprocess_negative_cycle(tmp_path: Path) -> None:
    p = tmp_path / "cycle.json"
    p.write_text(
        '{"directed": true, "edges": ['
        '{"source": "a", "target": "b", "weight": 1},'
        '{"source": "b", "target": "a", "weight": -2}]}',
        encoding="utf-8",
    )
    result = run_subprocess("shortest-path", str(p), "a", "b", "-a", "bellman-ford")
    assert result.returncode == 1
    assert "negative cycle" in result.stderr
    assert "Traceback" not in result.stderr


def test_subprocess_usage_error_exit_2() -> None:
    result = run_subprocess("toposort")
    assert result.returncode == 2
    assert "usage:" in result.stderr
