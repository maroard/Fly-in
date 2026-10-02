from pathlib import Path

import pytest
from tuiloom import AnimationFrame, CommandContext, KeyBinding
from tuiloom.input_handler.input_event import InputEvent

from src.application import Application, SimulationMode
from src.domain.graph import Graph
from src.parsing.parser import Parser
from src.rendering.renderer import Renderer
from src.ui.menus import main_menu


MAP_PATH = (
    Path(__file__).resolve().parents[1] / "maps/easy/01_linear_path.txt"
)
EXPECTED_OUTPUT = (
    "D1-waypoint1\n"
    "D1-waypoint2 D2-waypoint1\n"
    "D1-goal D2-waypoint2\n"
    "D2-goal\n"
)


@pytest.fixture
def output_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate the project output and launch from a different directory."""
    monkeypatch.setattr(
        main_menu, "__file__", str(tmp_path / "src/ui/menus/main_menu.py")
    )
    working_directory = tmp_path / "working_directory"
    working_directory.mkdir()
    monkeypatch.chdir(working_directory)
    return tmp_path / "output.txt"


def run(mode: SimulationMode, map_path: Path = MAP_PATH) -> Application:
    """Start a real simulation through the main menu command."""
    application = Application()
    application.simulation_mode = mode
    application.map_path = map_path
    application.graph = Graph(Parser(map_path).process())
    application.renderer = Renderer(application.graph)
    menu = application.main_menu
    command = next(
        item for item in menu.commands if item.label == "Run simulation"
    )
    command.callback(CommandContext(menu.app, menu, command, None))
    return application


def tick(application: Application, elapsed: float) -> None:
    """Advance the menu tick to a given playback time."""
    handle = application.playback_tick
    assert handle is not None
    handle.callback(AnimationFrame(elapsed, round(elapsed * handle.fps)))


@pytest.mark.parametrize("mode", ["one_shot", "step_by_step"])
def test_output_is_created_only_after_playback_finishes(
    output_path: Path, mode: SimulationMode,
) -> None:
    application = run(mode)
    playback = application.playback
    assert playback is not None
    assert not output_path.exists()
    tick(application, 0.0)

    if mode == "one_shot":
        tick(application, application.seconds_per_movement)
        assert not output_path.exists()
        tick(
            application, len(playback.turns) * application.seconds_per_movement
        )
    else:
        menu = application.main_menu
        menu._focused_panel = application.graph_panel
        elapsed = 0.0
        while not playback.finished:
            assert not output_path.exists()
            menu._handle_event(InputEvent(KeyBinding(" ")))
            elapsed += application.seconds_per_movement
            tick(application, elapsed)

    assert playback.finished
    assert output_path.read_text(encoding="utf-8") == EXPECTED_OUTPUT
    assert not Path("output.txt").exists()

    modified = output_path.stat().st_mtime_ns
    panel = application.simulation_panel
    assert panel is not None
    panel.select_item(0)
    tick(application, playback.last_elapsed + 1.0)
    assert output_path.stat().st_mtime_ns == modified
    assert output_path.read_text(encoding="utf-8") == EXPECTED_OUTPUT


def test_completed_simulation_replaces_previous_output(
    output_path: Path,
) -> None:
    output_path.write_text("Previous result\n", encoding="utf-8")
    application = run("one_shot")
    assert output_path.read_text(encoding="utf-8") == "Previous result\n"
    tick(application, 0.0)
    tick(application, 10.0)
    assert output_path.read_text(encoding="utf-8") == EXPECTED_OUTPUT


def test_output_includes_restricted_connection_movements(
    output_path: Path, tmp_path: Path,
) -> None:
    map_path = tmp_path / "restricted.txt"
    map_path.write_text(
        "nb_drones: 2\n"
        "start_hub: start 0 0\n"
        "end_hub: goal 1 0 [zone=restricted]\n"
        "connection: start-goal [max_link_capacity=2]\n",
        encoding="utf-8",
    )
    application = run("one_shot", map_path)
    tick(application, 0.0)
    tick(application, 10.0)
    assert output_path.read_text(encoding="utf-8") == (
        "D1-start-goal D2-start-goal\n"
        "D1-goal D2-goal\n"
    )


def test_output_error_is_shown_without_interrupting_completion(
    output_path: Path,
) -> None:
    output_path.mkdir()
    application = run("one_shot")
    tick(application, 0.0)
    tick(application, 10.0)
    assert application.playback is not None and application.playback.finished
    message = application.main_menu.display_state.message
    assert message is not None
    assert message.startswith("Could not write output.txt:")


def test_failed_simulation_preserves_previous_output(
    output_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed calculation must not replace a completed result."""
    def fail(simulator: main_menu.Simulator) -> None:
        raise RuntimeError("Simulation deadlock")

    output_path.write_text("Previous result\n", encoding="utf-8")
    monkeypatch.setattr(main_menu.Simulator, "simulate", fail)
    application = run("one_shot")
    assert application.playback is None
    assert application.main_menu.display_state.message == "Simulation deadlock"
    assert output_path.read_text(encoding="utf-8") == "Previous result\n"
