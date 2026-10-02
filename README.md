*This project has been created as part of the 42 curriculum by maroard.*

# Fly-in

## Description

Fly-in is an object-oriented Python application that routes a fleet of drones
from a start hub to an end hub through a network of connected zones. The goal
is to deliver every drone in as few simulation turns as possible while
respecting zone capacities, connection capacities and movement costs.

The application parses a text map, builds an undirected graph, computes a
simulation and displays an animated terminal interface. It offers two routing
strategies, automatic or step-by-step playback, movement inspection and a
plain-text output file following the format required by the
[project subject, version 1.6](subject.pdf).

Graph storage, pathfinding and movement scheduling are implemented in the
project. No graph library such as NetworkX or graphlib is used.

## Instructions

### Requirements and installation

- Python **3.12 or later**, as required by `pyproject.toml`.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency
  and virtual environment management.
- Make for the provided shortcuts.
- An interactive terminal supporting ANSI colors and Unicode characters.

From the repository root:

```sh
make install
make run
```

`make install` runs `uv sync`, installs dependencies from `uv.lock` and creates
the `.venv` environment. No compilation step is required.

The equivalent commands without Make are:

```sh
uv sync
uv run python -m src
```

Run the application from the repository root: map discovery uses the relative
`maps/` directory. Use a sufficiently large terminal to read the graph and the
side panels comfortably.

### Running a simulation

1. Select a category and a map in the initial **Map Menu**.
2. Open **Settings** to choose the routing strategy, playback mode and speed.
3. Choose **Run simulation** in the main menu.
4. Watch the animation or advance through the movements manually.
5. Once playback finishes, browse the recorded turns and inspect movements.
6. Read the generated `output.txt` in the repository root.

The default settings are **Single-path**, **One shot** and **Medium** speed.
Changing settings takes effect when starting a new simulation. To load another
map, use **Settings → Change map**.

| Control | Action |
| --- | --- |
| Arrow keys | Navigate menus, choices and selectable movement rows |
| Enter | Activate the selected menu item or confirm a choice |
| M | Show or hide the main menu |
| Tab | Change the focused content panel |
| Space | Start the next movement in step-by-step mode, with Graph or Simulation focused |
| Backspace | Undo the previous movement in step-by-step mode, with Graph or Simulation focused |
| Shift + Left / Right | Browse turns after playback finishes, with Simulation focused |
| Esc | Go back through menus or quit from the main screen |

### Makefile commands

| Command | Purpose |
| --- | --- |
| `make install` | Install runtime and development dependencies with uv |
| `make run` | Launch the terminal application |
| `make debug` | Launch through Python's `pdb` debugger |
| `make test` | Run the pytest suite |
| `make lint` | Run flake8 and mypy with the mandatory subject flags |
| `make lint-strict` | Run flake8 and `mypy --strict` |
| `make clean` | Remove Python caches, bytecode and `output.txt` |

The current `clean` rule uses `rm output.txt`; if no output file exists, that
last command reports an error after the caches have been removed.

## Map format and movement rules

Maps are UTF-8 text files. Blank lines and full-line comments beginning with
`#` are ignored. The first nonempty, noncomment line defines the fleet size:

```text
nb_drones: 5
```

Zones and connections use the following syntax:

```text
start_hub: start 0 0 [color=green]
end_hub: goal 10 0 [color=yellow]
hub: corridor 3 0 [zone=priority color=blue max_drones=2]
connection: start-corridor [max_link_capacity=2]
connection: corridor-goal
```

| Zone type | Cost to enter | Behavior |
| --- | --- | --- |
| `normal` | 1 turn | Standard accessible zone; default type |
| `priority` | 1 turn | Preferred when routes have equal movement cost |
| `restricted` | 2 turns | One turn on the connection, then arrival on the next turn |
| `blocked` | Inaccessible | Excluded from valid routes |

Zone metadata accepts `zone`, `color` and `max_drones`. Connection metadata
accepts `max_link_capacity`. Metadata is optional, enclosed in brackets, and
its entries may appear in any order. Default zone and connection capacities
are both **1**; the default color is unspecified.

The parser checks that:

- `nb_drones` is a positive integer and is defined once.
- Exactly one start hub and one end hub exist.
- Zone names are unique and contain no dashes or whitespace.
- Coordinates are integers, including negative values.
- Connections reference previously defined zones and are unique in both
  directions: `a-b` and `b-a` describe the same connection.
- Zone types, metadata syntax and metadata keys are valid; repeated metadata
  keys are rejected.
- Capacities on ordinary zones and connections are positive integers.

Start and end hubs have unlimited occupancy. Their `max_drones` metadata is
ignored. Colors accept single-word values rather than a fixed parser whitelist;
their display depends on terminal rendering support.

Each drone can move at most once per simulation turn. Departures free zone
capacity for arrivals in that same turn. Drones may wait in a zone when their
next move cannot be accepted. A drone entering a restricted zone must complete
its transit on the following turn; it cannot wait on the connection. Drones
reaching the end hub stop receiving movement intents.

Parsing failures include the line number, cause and offending line when
available. Unreachable destinations and simulation deadlocks are reported as
errors.

### Adding maps

Place a map in `maps/custom/`, or create another directory inside `maps/`.
The map menu discovers directories and their files on opening. Keep map files
in the documented text format. Supplied maps are grouped into `easy`, `medium`,
`hard` and `challenger`; custom maps provide additional stress cases.

## Algorithm choices and implementation strategy

### Graph representation and shortest paths

`Graph` stores zones in a dictionary, connections in a list and adjacency lists
indexed by zone name. Every connection is inserted into both endpoint adjacency
lists. Coordinates serve visualization; they do not determine route costs.

`PathFinder` implements **Dijkstra's algorithm** using the standard library's
`heapq` priority queue. Each transition is weighted by the destination zone:
restricted zones cost two turns, other accessible zones cost one. Blocked
zones and explicitly excluded resources are skipped.

Queue entries contain `(distance, negative_priority_count, zone_name)`. The
search minimizes distance first and, for equal distances, prefers routes
visiting more priority zones. Predecessor names reconstruct the final immutable
`Path`. This favors priority zones without treating them as cheaper than
ordinary zones.

### Routing strategies

**Single-path:** one initial shortest path is computed and shared by all
drones. Capacity checks determine when each drone can advance along it. This
creates a pipeline on linear maps and provides a deterministic baseline.

**Multi-path:** drones initially receive the same shortest path. When a move
is rejected, `Router` searches from that drone's current zone while excluding
the blocking zone or connection. If an alternative's first move is also
blocked, that resource is excluded and another search is attempted, up to
`number of zones + number of connections` attempts per rejected drone.

An alternative is accepted only when it can start immediately and its remaining
movement cost is **strictly less** than the current remaining cost plus one
turn of waiting. Previously accepted moves remain protected. The drone then
keeps its new route for subsequent turns.

This is a local congestion heuristic. It can distribute drones among available
branches, but it does not compute a globally optimal fleet schedule or explore
every possible future waiting pattern. Equal-cost alternatives to waiting are
not selected.

### Turn scheduling and capacity resolution

`Simulator.step()` performs these operations:

1. Complete restricted-zone transits from the previous turn. Arriving drones
   cannot move again in this turn.
2. Build movement intents for other undelivered drones.
3. Validate adjacency, accessibility and drone state.
4. Resolve connection limits, restricted destination reservations and projected
   zone occupancy.
5. In multi-path mode, try to reroute rejected intents.
6. Apply accepted moves, refresh occupancy and record the turn.

Zone occupancy is evaluated as `current occupancy - departures + arrivals`.
Restricted destination slots are reserved before a transit starts. When a
resource overflows, higher drone IDs are rejected first. Resolution repeats
until the accepted set stops shrinking, because rejecting a departure can
block another arrival. Rejected drones stay in place.

`simulate()` repeats turns until all drones are delivered. If a turn records no
movement while drones remain undelivered, it raises a deadlock error rather
than looping indefinitely.

### Reuse, complexity and memory

Let `V` be the number of zones, `E` the number of connections, `N` the number
of drones and `M` the number of recorded movement events.

- Graph storage uses `O(V + E)` memory, and fleet state uses `O(N)` memory.
- The usual heap-based Dijkstra baseline is `O((V + E) log V)`. This
  implementation may also revisit equal-distance states when their priority
  count improves. Rerouting adds list-based exclusion checks and repeated
  searches, so the baseline is not a bound for the entire simulation.
- Initial routing performs one search and shares its immutable result.
  Assigned routes are retained, but alternative search results have no global
  cache.
- Capacity resolution scans zones, connections and intents repeatedly. A
  conservative bound for a turn without rerouting is
  `O((V + E) N² + N² log N)`, accounting for repeated filtering, occupancy
  refreshes and overflow sorting. Actual work depends on congestion.
- The UI computes the complete simulation before playing it. Recording the
  history uses `O(M)` memory; retaining separate rerouted paths can use up to
  `O(NV)` memory.

There is no fixed fleet-size limit in the parser. Runtime and memory use still
grow with fleet size, graph size, congestion and recorded history.

## Visual representation

The terminal interface uses **Tuiloom** and displays the graph beside the
simulation, movement details and statistics panels.

- **Graph:** coordinates are projected onto terminal cells, connections are
  drawn between zones, and drone labels move between their recorded positions.
  Zone colors follow map metadata; unspecified colors render white, and
  `color=rainbow` enables animated color changes. Shared drone positions are
  grouped, and a selected drone is highlighted.
- **Simulation:** shows the movement records for the current turn. After
  completion, turn navigation and row selection allow inspection of history.
- **Movement:** shows the selected drone's zone or connection, its metadata,
  transit direction when applicable and other drones sharing that location.
- **Stats:** shows the current turn, movements in that turn and delivered
  drones. After completion, it adds the average arrival turn per drone and
  total path cost, computed as the number of recorded movement events.
- **Status bar:** shows readiness, running or completed state, the selected
  map when space permits, and controls for the focused panel.

Automatic playback animates the movements of a turn together. Step-by-step
playback presents one movement at a time and supports undo. These are two
views of the same precomputed simultaneous-turn simulation; playback does not
change its turn count or routing decisions.

Speed presets are **Low: 2 s**, **Medium: 1 s** and **High: 0.4 s**. A custom
duration accepts finite values from **0.1 to 30 seconds**. In automatic mode
the duration applies to the concurrently animated turn; in step-by-step mode
it applies to the selected movement.

Color, motion and inspection make branching routes, waiting, restricted
transits and capacity bottlenecks easier to follow. The layout adapts to
terminal dimensions, though small terminals can clip diagrams and controls.

## Example input and expected output

The supplied `maps/easy/01_linear_path.txt` contains:

```text
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

With either routing strategy, the expected output is:

```text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

The simulation takes **4 turns**. Drone D2 waits during the first turn, then
enters the space freed by D1. Waiting drones are omitted from output.

For a restricted end hub, this input:

```text
nb_drones: 2
start_hub: start 0 0
end_hub: goal 1 0 [zone=restricted]
connection: start-goal [max_link_capacity=2]
```

Produces:

```text
D1-start-goal D2-start-goal
D1-goal D2-goal
```

Each output line represents one simulation turn. Movement tokens use
`D<ID>-<zone>`, or `D<ID>-<connection>` during restricted-zone transit.
Connection names preserve the endpoint order from the input definition.

The UI writes `output.txt` **when playback finishes**, replacing the previous
result. Starting a simulation does not immediately replace that file. In
step-by-step mode, complete playback to save the new result. A failed
simulation calculation preserves the previous output; write errors are shown
in the menu.

### Running the engine without the interface

The entry point opens the interactive UI and has no map-path command-line
option. To print a simulation directly, use the Python classes:

```sh
uv run python - <<'PY'
from pathlib import Path
from src.domain.graph import Graph
from src.parsing.parser import Parser
from src.simulation.simulator import Simulator

graph = Graph(Parser(Path("maps/easy/01_linear_path.txt")).process())
simulator = Simulator(graph, routing_mode="multi-path")
simulator.simulate()
for turn in simulator.state.turns:
    print(" ".join(
        f"D{move.drone_id}-{move.destination}"
        for move in turn.movements
    ))
PY
```

This prints movement lines to standard output; it does not invoke the UI's
automatic file export.

## Performance and validation

The following counts were measured on the included maps using the simulation
engine. Animation speed does not affect these counts.

| Map | Drones | Subject target | Single-path | Multi-path |
| --- | ---: | ---: | ---: | ---: |
| Easy — Linear path | 2 | ≤ 6 | 4 | 4 |
| Easy — Simple fork | 4 | ≤ 8 | 6 | 5 |
| Easy — Basic capacity | 4 | ≤ 6 | 4 | 4 |
| Medium — Dead end trap | 5 | ≤ 12 | 8 | 8 |
| Medium — Circular loop | 6 | ≤ 15 | 15 | 15 |
| Medium — Priority puzzle | 5 | ≤ 12 | 8 | 8 |
| Hard — Maze nightmare | 8 | ≤ 30 | 13 | 13 |
| Hard — Capacity hell | 12 | ≤ 35 | 16 | 16 |
| Hard — Ultimate challenge | 15 | ≤ 45 | 26 | 26 |
| Challenger — The Impossible Dream | 25 | < 45 for bonus | 67 | 51 |

Both strategies meet the reference turn targets for the nine mandatory maps.
The Challenger map is solved, but the current implementation does **not** beat
its 45-turn reference record. Turn counts alone do not establish compliance
with every rule on every possible evaluation map.

The test suite covers parser validation, occupancy, playback, rendering,
navigation, settings and output export. At the documentation update,
`make test` passed **92 tests**, and `make lint` passed flake8 and mypy.
The optional strict command is available separately.

## Project structure and dependencies

```text
.
├── Makefile
├── README.md
├── pyproject.toml
├── uv.lock
├── maps/                 # Supplied maps and custom stress cases
├── src/
│   ├── __main__.py       # Application entry point
│   ├── application.py    # Shared resources and settings
│   ├── domain/           # Zones, connections, drones, graph and occupancy
│   ├── parsing/          # Text parser and validated map configuration
│   ├── pathfinding/      # Dijkstra search and routing strategies
│   ├── simulation/       # Intent resolution, turns and playback
│   ├── rendering/        # Projection, canvas and terminal drawing
│   └── ui/menus/         # Map, settings and simulation menus
└── tests/                # Automated regression tests
```

`output.txt` is generated after successful playback. Runtime dependencies are
`tuiloom==0.12.1` for the terminal interface and `pydantic==2.13.5` for metadata
validation. Development tools are pytest, flake8 and mypy. Python's standard
library supplies the heap, data classes and file handling.

## Resources

- [Fly-in subject](subject.pdf): requirements, movement rules, output format
  and reference benchmarks.
- [Map collection documentation](maps/README.md): descriptions of the supplied
  maps. Use the subject's benchmark table as the evaluation reference.
- [Dijkstra's original paper](https://doi.org/10.1007/BF01386390):
  *A note on two problems in connexion with graphs* (1959).
- [Python heapq documentation](https://docs.python.org/3/library/heapq.html):
  the standard library priority queue used by the pathfinder.
- [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/):
  dependency manager setup.
- [Pydantic documentation](https://docs.pydantic.dev/latest/): model validation.
- [pytest documentation](https://docs.pytest.org/en/stable/): automated testing.
- [flake8 documentation](https://flake8.pycqa.org/en/latest/) and
  [mypy documentation](https://mypy.readthedocs.io/en/stable/): style and static
  type checks.

### AI usage

AI tools were used as a support during the development of Fly-in, mainly to discuss architecture choices, review implementation ideas, identify edge cases, and help reason about pathfinding, simulation constraints, and code organization. The final implementation, design decisions, tests, and validation remain fully understood and controlled by the project author.
