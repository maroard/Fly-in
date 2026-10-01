from pathlib import Path

from tuiloom import AnimationFrame, CommandContext, KeyBinding
from tuiloom.input_handler.input_event import InputEvent

from src.application import Application, SimulationMode
from src.domain.graph import Graph
from src.parsing.parser import Parser
from src.rendering.renderer import Renderer


def run(mode: SimulationMode) -> Application:
    application = Application()
    application.simulation_mode = mode
    application.map_path = Path("maps/easy/01_linear_path.txt")
    application.graph = Graph(Parser(application.map_path).process())
    application.renderer = Renderer(application.graph)
    menu = application.main_menu
    command = next(
        item for item in menu.commands if item.label == "Run simulation"
    )
    command.callback(CommandContext(menu.app, menu, command, None))
    return application


def tick(application: Application, elapsed: float) -> None:
    handle = application.main_menu._tick_callbacks[0]
    handle.callback(AnimationFrame(elapsed, round(elapsed * handle.fps)))


def test_run_creates_three_panels_with_visible_unselected_turn() -> None:
    application = run("one_shot")
    assert application.graph_panel is not None
    assert application.output_panel is not None
    assert application.info_panel is not None
    assert application.graph_panel.content._kind == "animated"
    assert application.output_panel.content._kind == "selectable"
    assert application.output_panel.selected_item is None
    assert application.output_panel.content._selectable_items()[0].value == 1
    assert len(application.main_menu.content_panels) == 3


def test_step_space_starts_one_movement_only_in_graph_or_log_panel() -> None:
    application = run("step_by_step")
    menu = application.main_menu
    playback = application.playback
    assert playback is not None
    tick(application, 0.0)
    menu.show_menu()
    menu._focused_panel = None
    menu._handle_event(InputEvent(KeyBinding(" ")))
    assert playback.snapshot().positions[1].progress == 1.0
    menu.hide_menu()
    menu._focused_panel = application.graph_panel
    menu._handle_event(InputEvent(KeyBinding(" ")))
    tick(application, 0.5)
    assert playback.snapshot().positions[1].progress == 0.5
    menu._handle_event(InputEvent(KeyBinding(" ")))
    tick(application, 1.0)
    assert playback.completed_movements == 1


def test_turn_page_auto_advances_without_selecting_during_run() -> None:
    application = run("one_shot")
    menu = application.main_menu
    panel = application.output_panel
    playback = application.playback
    assert panel is not None and playback is not None
    menu._focused_panel = panel
    tick(application, 0.0)
    tick(application, application.seconds_per_movement)
    assert playback.turn_index == 1
    assert panel.content._kind == "selectable"
    assert "Turn 2:" in (panel.header or "")
    assert panel.selected_item is None
    menu._handle_event(InputEvent(KeyBinding("down")))
    assert panel.selected_item is None
    assert playback.snapshot().selected_drone_id is None


def test_rows_cannot_be_selected_during_either_simulation_mode() -> None:
    for mode in ("one_shot", "step_by_step"):
        application = run(mode)
        menu = application.main_menu
        panel = application.output_panel
        playback = application.playback
        assert panel is not None and playback is not None
        menu._focused_panel = panel
        assert panel.selected_item is None
        rows = panel.content._selectable_items()
        assert all(not row.enabled for row in rows)
        menu._handle_event(InputEvent(KeyBinding("down")))
        menu._handle_event(InputEvent(KeyBinding("up")))
        assert panel.selected_item is None
        assert playback.snapshot().selected_drone_id is None


def test_finished_panel_replays_first_row_after_arrow() -> None:
    application = run("one_shot")
    menu = application.main_menu
    panel = application.output_panel
    playback = application.playback
    assert panel is not None and playback is not None
    menu._focused_panel = panel
    tick(application, 0.0)
    tick(application, len(playback.turns) * application.seconds_per_movement)
    assert playback.finished
    assert panel.selected_item is None
    assert all(row.enabled for row in panel.content._selectable_items())
    final_positions = playback.snapshot().positions

    menu._handle_event(InputEvent(KeyBinding("up")))
    assert panel.selected_index == 0
    selected = panel.selected_item
    assert selected is not None
    assert playback.snapshot().selected_drone_id == selected.value
    assert playback.snapshot().positions == final_positions
    menu._handle_event(InputEvent(KeyBinding("down")))
    assert panel.selected_index == 0


def test_shift_turn_selects_first_movement_after_finish() -> None:
    application = run("one_shot")
    menu = application.main_menu
    panel = application.output_panel
    playback = application.playback
    assert panel is not None and playback is not None
    menu._focused_panel = panel
    tick(application, 0.0)
    tick(application, len(playback.turns) * application.seconds_per_movement)
    menu._handle_event(InputEvent(KeyBinding("left", shift=True)))
    assert "Turn 3:" in (panel.header or "")
    assert panel.selected_index == 0
    selected = panel.selected_item
    assert selected is not None and isinstance(selected.value, int)
    assert playback.snapshot().selected_drone_id == selected.value
    selected_drone = selected.value
    assert playback.snapshot().positions[selected_drone].end.zone == (
        playback.turns[2].movements[0].destination
    )
    assert playback.snapshot().positions[2].end.zone == "waypoint1"
    panel.clear_selection()
    assert playback.snapshot().positions[2].end.zone == "goal"
    menu._handle_event(InputEvent(KeyBinding("up")))
    assert panel.selected_index == 0
    assert playback.snapshot().positions[2].end.zone == "waypoint1"
    menu._handle_event(InputEvent(KeyBinding("down")))
    assert panel.selected_index == 1
    selected = panel.selected_item
    assert selected is not None
    assert playback.snapshot().selected_drone_id == selected.value
    assert playback.snapshot().positions[2].end.zone == "waypoint2"
