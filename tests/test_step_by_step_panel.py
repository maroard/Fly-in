from pathlib import Path
import re

from tuiloom import (
    AnimationFrame,
    CommandContext,
    KeyBinding,
    SelectableItem,
    style,
)
from tuiloom.input_handler.input_event import InputEvent
from tuiloom.render.menu_renderer import MenuRenderer
from tuiloom.render.terminal_renderer import TerminalRenderer

from src.application import Application
from src.domain.graph import Graph
from src.parsing.parser import Parser
from src.rendering.renderer import Renderer


def start_simulation(application: Application) -> None:
    path = Path("maps/easy/01_linear_path.txt")
    application.map_path = path
    application.map_config = Parser(path).process()
    application.graph = Graph(application.map_config)
    application.renderer = Renderer(application.graph)
    menu = application.main_menu
    command = next(
        item for item in menu.commands if item.label == "Run simulation"
    )
    command.callback(CommandContext(menu.app, menu, command, None))


def panel_lines(application: Application) -> list[str]:
    panel = application.output_panel
    assert panel is not None
    return [
        row.content if isinstance(row, SelectableItem) else row
        for row in panel.content._selectable_rows()
    ]


def status(application: Application, width: int = 180) -> str:
    menu = application.main_menu
    renderer = TerminalRenderer(
        menu=menu, menu_renderer=MenuRenderer(menu), content_spacing=True
    )
    return renderer._compose_frame(width, 40)[-1]


def finish_step_playback(application: Application) -> None:
    menu = application.main_menu
    panel = application.output_panel
    simulator = application.simulator
    handle = application.playback_tick
    assert panel is not None and simulator is not None and handle is not None
    menu._focused_panel = panel
    elapsed = 0.0
    handle.callback(AnimationFrame(elapsed, 0))
    for turn in simulator.state.turns:
        for _ in turn.movements:
            menu._handle_event(InputEvent(KeyBinding(" ")))
            elapsed += application.seconds_per_movement
            handle.callback(
                AnimationFrame(elapsed, round(elapsed * handle.fps))
            )


def test_step_by_step_shows_one_turn_and_one_movement_per_line() -> None:
    application = Application()
    application.simulation_mode = "step_by_step"
    start_simulation(application)
    simulator = application.simulator
    assert simulator is not None
    assert len(simulator.state.turns) > 1
    first = simulator.state.turns[0]
    rows = panel_lines(application)
    assert rows == [
        f"D-{move.drone_id}-{move.destination}"
        for move in first.movements
    ]
    panel = application.output_panel
    assert panel is not None
    assert panel.header == style("Turn 1:", bold=True)
    assert "[Space] Next move" in status(application)
    assert "[Space] Next move" in status(application, width=42)


def test_turn_title_uses_the_whole_panel_width() -> None:
    application = Application()
    start_simulation(application)
    menu = application.main_menu
    panel = application.output_panel
    assert panel is not None
    renderer = TerminalRenderer(
        menu=menu, menu_renderer=MenuRenderer(menu), content_spacing=True
    )

    for terminal_width in (100, 120):
        frame = renderer._compose_frame(terminal_width, 26)
        viewport = panel._runtime.viewport
        assert viewport is not None
        title_row = next(row for row in frame if "Turn 1:" in row)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", title_row)
        assert plain.split("┊")[-2] == "Turn 1:".center(viewport.width)


def test_shift_arrows_browse_turns_after_playback() -> None:
    application = Application()
    application.simulation_mode = "step_by_step"
    start_simulation(application)
    menu = application.main_menu
    panel = application.output_panel
    simulator = application.simulator
    assert panel is not None and simulator is not None
    assert len(panel.key_commands) == 3
    menu._focused_panel = panel
    menu._handle_event(InputEvent(KeyBinding("right", shift=True)))
    assert panel.header == style("Turn 1:", bold=True)

    finish_step_playback(application)
    assert application.playback is not None and application.playback.finished
    assert panel.header == style("Turn 4:", bold=True)
    assert "[Shift+←/→] Turns" in status(application)
    assert "[Shift+←/→] Turns" in status(application, width=42)
    menu._handle_event(InputEvent(KeyBinding("left", shift=True)))
    assert panel.header == style("Turn 3:", bold=True)
    menu._handle_event(InputEvent(KeyBinding("right", shift=True)))
    assert panel.header == style("Turn 4:", bold=True)


def test_switching_to_one_shot_removes_space_command() -> None:
    application = Application()
    application.simulation_mode = "step_by_step"
    start_simulation(application)
    panel = application.output_panel
    assert panel is not None
    assert len(panel.key_commands) == 3
    application.simulation_mode = "one_shot"
    menu = application.main_menu
    command = next(
        item for item in menu.commands if item.label == "Run simulation"
    )
    command.callback(CommandContext(menu.app, menu, command, None))
    assert application.output_panel is panel
    assert len(panel.key_commands) == 2
    assert panel.content._kind == "selectable"
    assert application.graph_panel is not None
    assert application.graph_panel.key_commands == ()
    assert "[Space]" not in status(application)
