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


def test_run_creates_three_panels_and_selectable_first_turn() -> None:
    application = run("one_shot")
    assert application.graph_panel is not None
    assert application.output_panel is not None
    assert application.info_panel is not None
    assert application.graph_panel.content._kind == "animated"
    assert application.output_panel.content._kind == "selectable"
    assert application.output_panel.selected_item is not None
    assert application.output_panel.selected_item.value == 1
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


def test_log_selection_marks_drone_and_turn_page_auto_advances() -> None:
    application = run("one_shot")
    menu = application.main_menu
    panel = application.output_panel
    playback = application.playback
    assert panel is not None and playback is not None
    menu._focused_panel = panel
    panel.select_item(0)
    assert playback.snapshot().selected_drone_id == 1
    tick(application, 0.0)
    tick(application, application.seconds_per_movement)
    assert playback.turn_index == 1
    assert panel.content._kind == "selectable"
    assert "Turn 2:" in (panel.header or "")
    first = panel.selected_item
    assert first is not None
    menu._handle_event(InputEvent(KeyBinding("down")))
    second = panel.selected_item
    assert second is not None and second.value != first.value
    assert playback.snapshot().selected_drone_id == second.value
