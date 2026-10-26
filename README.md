# graphkit

A small, readable graph-algorithms toolkit written in pure, standard-library
Python. It provides a weighted graph data structure (directed or undirected)
and the classic algorithms taught in an algorithms course: BFS, DFS,
Dijkstra, Bellman-Ford, A\*, topological sort, connected components and
Prim's minimum spanning tree.

The goal is clarity and correctness rather than raw speed: every function is
fully type-hinted, documented, and covered by tests that check textbook
examples with known answers.

## Install

Requires Python 3.10 or newer. There are no runtime dependencies.

```bash
pip install -e ".[dev]"
```

## Usage

```python
from graphkit import Graph, shortest_path, bellman_ford, topological_sort, NoPathError

# Undirected weighted graph (nodes can be any hashable value)
g: Graph[str] = Graph()
g.add_edge("A", "B", 4)
g.add_edge("A", "C", 1)
g.add_edge("C", "B", 2)
g.add_edge("B", "D", 5)

path, cost = shortest_path(g, "A", "D")
print(path, cost)            # ['A', 'C', 'B', 'D'] 8.0

g.add_node("Z")              # isolated node
try:
    shortest_path(g, "A", "Z")
except NoPathError as err:
    print(err)               # no path from 'A' to 'Z'

# Directed graph with a negative edge -> use Bellman-Ford
d: Graph[str] = Graph(directed=True)
d.add_edge("s", "a", 2)
d.add_edge("a", "b", -1)
d.add_edge("s", "b", 4)
dist, pred = bellman_ford(d, "s")
print(dist)                  # {'s': 0.0, 'a': 2.0, 'b': 1.0}

# Task ordering
tasks: Graph[str] = Graph(directed=True)
tasks.add_edge("design", "build")
tasks.add_edge("build", "test")
print(topological_sort(tasks))   # ['design', 'build', 'test']
```

Other functions: `bfs`, `dfs`, `bfs_shortest_path`, `dijkstra`, `astar`,
`connected_components`, `prim_mst`, `reconstruct_path`, and the file
helpers `load_graph`, `save_graph`, `read_csv`, `write_csv`, `read_json`,
`write_json`.

## Quick start / end-to-end demo

```bash
cd graph-toolkit
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check . && pytest        # lint + 222 tests
```

The `graphkit` command (also `python -m graphkit`) runs the algorithms on a
graph file. Three example datasets are bundled in `data/`:

| File | What it is |
|---|---|
| `uk_roads.csv` | 24 UK cities with approximate road distances in km (undirected). Belfast and Derry have no road link to Great Britain, so the graph has two components. |
| `project_tasks.csv` | Task dependencies for shipping a small web app (a DAG: each row means *source must finish before target*). |
| `lake_district_ev.json` | Energy in kWh for an electric car between Lake District towns (directed). Downhill legs are negative because of regenerative braking, so Dijkstra refuses it and Bellman-Ford is needed. |

Real output:

```console
$ graphkit info data/uk_roads.csv
File:          data/uk_roads.csv
Type:          undirected
Nodes:         24
Edges:         35
Total weight:  4,172
Weight range:  40 to 235
Negative edges: 0
Self-loops:    0
Isolated nodes: 0
Components:    2

$ graphkit shortest-path data/uk_roads.csv London Edinburgh
Shortest path from London to Edinburgh (dijkstra):
  London -> Cambridge -> Nottingham -> Sheffield -> Leeds -> Newcastle -> Edinburgh
  Total weight: 689  (6 edges)
  Legs:
    London -> Cambridge: 98
    Cambridge -> Nottingham: 135
    Nottingham -> Sheffield: 61
    Sheffield -> Leeds: 55
    Leeds -> Newcastle: 150
    Newcastle -> Edinburgh: 190

$ graphkit shortest-path data/uk_roads.csv Plymouth Aberdeen --algorithm bfs
Shortest path from Plymouth to Aberdeen (bfs):
  Plymouth -> Exeter -> Bristol -> Birmingham -> Manchester -> Carlisle -> Glasgow -> Aberdeen
  Edges: 7 (weights ignored)

$ graphkit shortest-path data/lake_district_ev.json Kendal Patterdale --algorithm bellman-ford
Shortest path from Kendal to Patterdale (bellman-ford):
  Kendal -> Windermere -> Kirkstone Pass -> Patterdale
  Total weight: 5  (3 edges)
  Legs:
    Kendal -> Windermere: 2.3
    Windermere -> Kirkstone Pass: 3.5
    Kirkstone Pass -> Patterdale: -0.8

$ graphkit mst data/uk_roads.csv
Minimum spanning forest (2 trees): 22 edges, total weight 2,109
  London - Brighton              86
  London - Oxford                90
  London - Cambridge             98
  Cambridge - Norwich           102
  Brighton - Southampton        105
  Oxford - Birmingham           109
  Birmingham - Nottingham        85
  Nottingham - Sheffield         61
  Sheffield - Leeds              55
  Leeds - York                   40
  Sheffield - Manchester         61
  Manchester - Liverpool         56
  Oxford - Bristol              120
  Bristol - Cardiff              70
  Bristol - Exeter              122
  Exeter - Plymouth              72
  York - Newcastle              140
  Newcastle - Carlisle           95
  Carlisle - Glasgow            155
  Glasgow - Edinburgh            75
  Edinburgh - Aberdeen          195
  Belfast - Derry               117

$ graphkit components data/uk_roads.csv
2 connected components:
  1. (22 nodes) London, Cambridge, Oxford, Brighton, Southampton, Birmingham, Norwich, Nottingham, Bristol, Cardiff, Exeter, Plymouth, Manchester, Sheffield, Leeds, Liverpool, Carlisle, York, Newcastle, Edinburgh, Glasgow, Aberdeen
  2. (2 nodes) Belfast, Derry

$ graphkit toposort data/project_tasks.csv
Topological order (12 nodes):
   1. gather-requirements
   2. set-up-ci
   3. design-database
   4. design-ui
   5. build-api
   6. write-api-tests
   7. build-frontend
   8. write-ui-tests
   9. staging-deploy
  10. user-acceptance-testing
  11. production-release
  12. announce-launch
```

Errors are one readable line on stderr with exit code 1 (bad command-line
usage exits with 2, from `argparse`); there is never a traceback:

```console
$ graphkit shortest-path data/uk_roads.csv London Belfast
graphkit: error: no path from 'London' to 'Belfast'
$ graphkit shortest-path data/uk_roads.csv London Paris
graphkit: error: node 'Paris' is not in the graph
$ graphkit shortest-path data/lake_district_ev.json Kendal Patterdale
graphkit: error: edge ('Kirkstone Pass', 'Windermere') has negative weight -1; dijkstra needs non-negative weights, use --algorithm bellman-ford
$ graphkit info data/missing.csv
graphkit: error: cannot read data/missing.csv: No such file or directory
```

### CLI reference

| Command | Purpose |
|---|---|
| `graphkit shortest-path FILE SOURCE TARGET [-a dijkstra\|bellman-ford\|bfs] [-d]` | Cheapest (or fewest-edge, with `bfs`) route. `-d/--directed` treats CSV edges as one-way. |
| `graphkit mst FILE` | Minimum spanning tree/forest (Prim). Undirected graphs only. |
| `graphkit components FILE` | Connected components. Undirected graphs only. |
| `graphkit toposort FILE` | Topological order. The file is always read as directed. |
| `graphkit info FILE [-d]` | Node/edge counts, weight range, components or DAG check. |

## File formats

`graphkit.load_graph(path)` / `save_graph(graph, path)` pick the format from
the extension; `read_csv`, `write_csv`, `read_json` and `write_json` are
also available.

**CSV edge list** - header `source,target,weight` (the weight column is
optional; an empty weight means 1). A row with an empty target declares an
isolated node. Blank lines and `#` comments are skipped. CSV cannot record
direction, so pass `directed=True` (or `--directed`) when needed.

```csv
source,target,weight
London,Cambridge,98
Cambridge,Norwich,102
```

**JSON** - `directed` and `nodes` are optional; node labels are strings or
integers.

```json
{"directed": false,
 "nodes": ["Belfast", "Derry"],
 "edges": [{"source": "Belfast", "target": "Derry", "weight": 117}]}
```

Malformed files raise `GraphFormatError` (a `GraphError`) naming the file
and, for CSV, the line: wrong header or column count, non-numeric, NaN or
infinite weights, empty labels, and duplicate edges (which would otherwise
silently overwrite each other) are all rejected.

## Algorithms

V = number of nodes, E = number of edges.

| Algorithm | Time | Extra space |
|---|---|---|
| BFS | O(V + E) | O(V) |
| DFS (iterative) | O(V + E) | O(V) |
| Unweighted shortest path (BFS) | O(V + E) | O(V) |
| Dijkstra (binary heap) | O((V + E) log V) | O(V + E) |
| A\* (binary heap) | O((V + E) log V) worst case | O(V + E) |
| Bellman-Ford | O(V · E) | O(V + E) |
| Topological sort (Kahn) | O(V + E) | O(V) |
| Connected components | O(V + E) | O(V) |
| Prim's MST (binary heap) | O(E log V) | O(E) |

**Breadth-first search (BFS)** explores outward in rings: the start node,
then everything one step away, then two steps away, and so on. Because of
this, the first time BFS reaches a node it has used the fewest possible
edges, which is why it also gives the unweighted shortest path.

**Depth-first search (DFS)** follows one route as far as it can before
backing up to try the next. It is written with an explicit stack instead of
recursion, so very deep graphs cannot hit Python's recursion limit.

**Dijkstra's algorithm** finds the cheapest route from one node to all
others when no edge has a negative cost. It always settles the closest
not-yet-settled node next, using a priority queue (a binary heap from
`heapq`). Python's heap cannot lower an entry's priority, so the code uses
*lazy deletion*: it pushes a new, cheaper entry and skips outdated ones when
they are popped. Each heap entry carries a counter so that ties never
compare nodes directly, which means nodes do not need to be sortable. Each
edge can add at most one heap entry, and each heap operation costs
O(log E) = O(log V), giving O((V + E) log V).

**Bellman-Ford** also finds cheapest routes but tolerates negative edge
costs. It repeatedly "relaxes" every edge (checks whether going through it
gives a cheaper route); after V − 1 rounds all true shortest paths are
found. If a further round still finds an improvement, there must be a loop
whose total cost is negative, so shortest paths are undefined and a
`NegativeCycleError` is raised. It stops early once a round changes nothing.
In an undirected graph, a single negative edge counts as a negative cycle
(you can walk back and forth along it).

**A\*** is Dijkstra with a sense of direction: it prioritises nodes by
"cost so far + estimated cost to the goal". With a good estimate (for
example, Manhattan distance on a grid) it explores far fewer nodes. It is
guaranteed optimal when the estimate never overestimates.

**Topological sort (Kahn's algorithm)** orders tasks so every task comes
after the ones it depends on. It repeatedly takes a node with no remaining
incoming edges. If nodes are left over that always have an incoming edge,
they are part of a cycle and a `GraphCycleError` is raised.

**Connected components** groups the nodes of an undirected graph into
islands that are reachable from each other, by running BFS from each
not-yet-seen node.

**Prim's algorithm** builds a minimum spanning tree: the cheapest set of
edges that connects every node. It grows a tree by always adding the
cheapest edge to a new node. On a disconnected graph it returns one tree per
component (a spanning forest).

## Design choices

- **Adjacency map (`dict[node, dict[neighbour, weight]]`).** Adding a node,
  adding an edge, and checking whether an edge exists are all O(1) on
  average, and iterating over a node's neighbours costs O(degree). This
  suits sparse graphs, which most real graphs are. An adjacency matrix
  would need O(V²) memory regardless of how many edges exist.
- **Insertion-ordered dicts** (guaranteed since Python 3.7) make every
  traversal deterministic and testable.
- **Generics.** `Graph[N]` is generic over a hashable node type, so a
  `Graph[str]` or `Graph[tuple[int, int]]` is checked by type checkers.
- **`collections.deque`** for BFS/Kahn queues (O(1) pops from the left),
  **`list`** as a stack for DFS, **`heapq`** for priority queues, and
  **`set`** for visited checks.
- **Simple graphs only.** Adding an existing edge overwrites its weight;
  parallel edges are not supported. Self-loops are allowed.
- **Validation.** Weights must be finite `int`/`float` values (NaN,
  infinity and booleans are rejected).

### Unreachable nodes

Single-source functions (`dijkstra`, `bellman_ford`) return dictionaries
that contain **only reachable nodes**; an unreachable node is simply
absent. Point-to-point functions (`shortest_path`, `astar`,
`bfs_shortest_path`) raise **`NoPathError`**. An exception was preferred
over returning `None` because a missing route usually needs handling, and an
exception cannot be ignored by accident.

### Exceptions

All derive from `GraphError`:

| Exception | Raised when |
|---|---|
| `NodeNotFoundError` | a node passed to a function is not in the graph |
| `EdgeNotFoundError` | removing or reading the weight of a missing edge |
| `NegativeWeightError` | Dijkstra or A\* is given a negative edge |
| `NegativeCycleError` | Bellman-Ford finds a reachable negative cycle |
| `GraphCycleError` | topological sort is given a graph with a cycle |
| `NoPathError` | the target cannot be reached from the source |
| `GraphFormatError` | a CSV or JSON graph file is malformed |

`ValueError` is raised when an algorithm is used on the wrong kind of graph
(e.g. topological sort on an undirected graph), and `TypeError`/`ValueError`
for invalid weights.

## Running the tests

```bash
pytest
```

CI (GitHub Actions) runs `ruff check .` and `pytest` on Python 3.10 to 3.13.

The tests cover textbook graphs from *Introduction to Algorithms* (CLRS)
with known answers, a seeded random cross-check of Dijkstra against
Bellman-Ford on 50 graphs, directed vs. undirected behaviour, disconnected
graphs, self-loops, single-node graphs, and every error path. `test_io.py`
covers CSV/JSON round trips and malformed files; `test_cli.py` runs the CLI
end to end, both in-process and as a real `python -m graphkit` subprocess,
on the bundled data and temporary files, including every error path.

## Project layout

```
graph-toolkit/
  pyproject.toml          package metadata, `graphkit` script, ruff/pytest config
  README.md
  .github/workflows/
    ci.yml                lint + tests on Python 3.10-3.13
  data/
    uk_roads.csv          UK road network (undirected, km)
    project_tasks.csv     task-dependency DAG
    lake_district_ev.json EV energy graph with negative edges (directed)
  src/graphkit/
    __init__.py           public API
    __main__.py           `python -m graphkit`
    cli.py                argparse command-line interface
    io.py                 CSV / JSON loading and saving
    graph.py              Graph class
    traversal.py          BFS, DFS, BFS shortest path, topological sort, components
    shortest_paths.py     Dijkstra, Bellman-Ford, A*
    mst.py                Prim's minimum spanning tree
    exceptions.py         exception hierarchy
  tests/
    conftest.py           shared textbook graphs
    test_graph.py
    test_traversal.py
    test_shortest_paths.py
    test_mst.py
    test_io.py            file formats
    test_cli.py           end-to-end CLI tests
```
