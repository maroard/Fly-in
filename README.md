# Fly-in

A drone routing and simulation application with a terminal interface.

```sh
make install
make run
```

Select a map, choose a mode and speed in **Settings**, then choose
**Run simulation**. The screen has three panels:

- **Graph** animates drones along connections. It shows `D3` for one drone or
  `x4` for a group. A drone entering a restricted zone stops halfway until the
  following turn.
- **Simulation** shows one turn at a time, with one selectable movement per
  line. Focus it with Tab and use Up/Down to locate a drone on the graph.
- **Info** shows the current turn, delivered drones, movements in
  that turn, total turns, and final scoring metrics.

**One shot** animates each turn automatically. Drones in the same turn move
together. In **Step by step**, focus Graph or Simulation and press Space to
animate the next movement. Repeated presses during a movement are ignored.
After the simulation, focus Simulation and use Shift+Left/Right to review turns.

**Simulation speed** sets the duration of each movement: Low 2 seconds,
Medium 1 second, High 0.4 seconds, or Custom from 0.1 to 30 seconds.

Rerunning a simulation reuses the panel handles. Changing maps removes the
three panels and resets playback.

## Status bar example

The main menu installs a responsive status bar in
`src/ui/menus/main_menu.py`. It reads the current map, playback and focus:

```text
READY │ Map: easy/01_linear_path.txt │ Turn 0 │ 0/2 delivered │ [M] Menu │ [Esc] Quit
RUNNING │ Map: easy/01_linear_path.txt │ Turn 1/4 │ 0/2 delivered │ [M] Menu │ [Tab] Focus │ [Esc] Quit
DONE │ Turn 4/4 │ 2/2 delivered │ [Shift+←/→] Turns │ [↑/↓] Locate │ [Esc] Quit
```

The renderer receives the available terminal width in cells. Fly-in chooses a
full, medium, or compact string. The API pattern is:

```python
from tuiloom import StatusBar


def render_status(width: int) -> str:
    # Read application state and choose wording that fits this width.
    playback = application.playback
    turn = playback.turn_index + 1 if playback is not None else 0
    return f"Turn {turn}" if width >= 20 else f"T{turn}"


menu.set_status_bar(StatusBar.responsive(render_status))
# After changing the displayed turn at the same terminal width:
menu.refresh_status_bar()
```

Responsive status text is reevaluated on width or focus changes and explicit
refresh. Fly-in refreshes it as playback advances. Status callbacks only read
state; Tuiloom's menu tick callback updates the panels on the UI thread, while
the animated graph producer reads a snapshot on its worker thread.

The development dependency points to the local editable Tuiloom checkout
configured in `pyproject.toml`.

```sh
make test
make lint
```

The interface uses `MenuDisplay`, `display_state`,
`add_submenu()` and `callback`. ANSI text colors use `foreground`.
