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
`connected_components`, `prim_mst`, `reconstruct_path`.

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

`ValueError` is raised when an algorithm is used on the wrong kind of graph
(e.g. topological sort on an undirected graph), and `TypeError`/`ValueError`
for invalid weights.

## Running the tests

```bash
pytest
```

The tests cover textbook graphs from *Introduction to Algorithms* (CLRS)
with known answers, a seeded random cross-check of Dijkstra against
Bellman-Ford on 50 graphs, directed vs. undirected behaviour, disconnected
graphs, self-loops, single-node graphs, and every error path.

## Project layout

```
graph-toolkit/
  pyproject.toml
  src/graphkit/
    __init__.py         public API
    graph.py            Graph class
    traversal.py        BFS, DFS, BFS shortest path, topological sort, components
    shortest_paths.py   Dijkstra, Bellman-Ford, A*
    mst.py              Prim's minimum spanning tree
    exceptions.py       exception hierarchy
  tests/
```
