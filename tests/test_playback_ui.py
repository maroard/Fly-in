from pathlib import Path

import pytest
from blessed import Terminal
from blessed.keyboard import resolve_sequence
from tuiloom import (
    AnimationFrame, CommandContext, KeyBinding, ScreenContent, SelectableItem,
)
from tuiloom.input_handler.input_event import InputEvent
from tuiloom.input_handler.input_handler import normalize_keystroke

from src.application import Application, SimulationMode
from src.domain.graph import Graph
from src.parsing.parser import Parser
from src.rendering.renderer import Renderer
from src.simulation.playback import Playback
from src.simulation.turn import Movement, Turn


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


@pytest.mark.parametrize("raw", ["\x1b[32;2u", "\x7f"])
def test_decoded_terminal_shortcut_rewinds_from_any_panel(raw: str) -> None:
    application = run("step_by_step")
    menu = application.main_menu
    playback = application.playback
    assert playback is not None
    tick(application, 0)
    menu._focused_panel = application.graph_panel
    menu._handle_event(InputEvent(KeyBinding(" ")))
    tick(application, 1)
    assert playback.completed_movements == 1
    terminal = Terminal()
    key = resolve_sequence(
        raw, terminal._keymap, terminal._keycodes,
        terminal._keymap_prefixes,
    )
    menu._focused_panel = application.movement_panel
    menu._handle_event(normalize_keystroke(key))
    assert playback.completed_movements == 0
    assert playback.snapshot().positions[1].end.zone == "start"
    assert application.simulation_panel is not None
    assert application.simulation_panel.selected_index == 0


def test_run_creates_three_panels_with_visible_unselected_turn() -> None:
    application = run("one_shot")
    assert application.graph_panel is not None
    assert application.simulation_panel is not None
    assert application.stats_panel is not None
    assert application.graph_panel.content._kind == "animated"
    assert application.simulation_panel.content._kind == "selectable"
    assert application.simulation_panel.selected_item is None
    rows = application.simulation_panel.content._selectable_items()
    assert rows[0].value == 1
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


def test_step_selection_follows_moves_and_global_back_updates_panels() -> None:
    application = run("step_by_step")
    menu = application.main_menu
    playback = application.playback
    panel = application.simulation_panel
    assert playback is not None and panel is not None
    assert panel.selected_index == 0
    assert playback.snapshot().selected_drone_id == 1
    details = application.movement_panel
    assert details is not None
    assert "Zone: start" in details.content._static_value()
    tick(application, 0)
    menu._focused_panel = application.graph_panel
    menu._handle_event(InputEvent(KeyBinding(" ")))
    tick(application, 1)
    assert "Turn 2:" in (panel.header or "")
    assert panel.selected_index == 0
    menu._handle_event(InputEvent(KeyBinding(" ")))
    tick(application, 2)
    assert panel.selected_index == 1
    assert playback.snapshot().selected_drone_id == 2
    details = application.movement_panel
    assert details is not None
    assert "Drone: D-2" in details.content._static_value()

    menu._focused_panel = details
    menu._handle_event(InputEvent(KeyBinding(" ", shift=True)))
    assert playback.completed_movements == 1
    assert panel.selected_index == 0
    assert playback.snapshot().selected_drone_id == 1
    assert "Zone: waypoint1" in details.content._static_value()
    assert application.stats_panel is not None
    assert "Movements: 0/2" in (
        application.stats_panel.content._static_value()
    )
    menu.show_menu()
    menu._focused_panel = None
    menu._handle_event(InputEvent(KeyBinding(" ", shift=True)))
    assert playback.completed_movements == 0
    assert "Turn 1:" in (panel.header or "")
    assert panel.selected_index == 0
    assert playback.snapshot().positions[1].end.zone == "start"
    menu._handle_event(InputEvent(KeyBinding(" ", shift=True)))
    assert playback.completed_movements == 0


def test_step_arrows_are_locked_until_finish_and_again_after_rewind() -> None:
    application = run("step_by_step")
    menu = application.main_menu
    playback = application.playback
    panel = application.simulation_panel
    assert playback is not None and panel is not None
    menu._focused_panel = panel

    def assert_locked() -> None:
        index = panel.selected_index
        snapshot = playback.snapshot()
        details = application.movement_panel
        assert details is not None
        lines = details.content._static_value()
        assert sum(
            row.enabled for row in panel.content._selectable_items()
        ) == 1
        for key in ("up", "down"):
            menu._handle_event(InputEvent(KeyBinding(key)))
            assert panel.selected_index == index
            assert playback.snapshot() == snapshot
            assert details.content._static_value() == lines

    elapsed = 0.0
    tick(application, elapsed)
    while not playback.finished:
        assert_locked()
        menu._handle_event(InputEvent(KeyBinding(" ")))
        assert_locked()
        elapsed += application.seconds_per_movement
        tick(application, elapsed)
    assert all(row.enabled for row in panel.content._selectable_items())
    menu._handle_event(InputEvent(KeyBinding("left", shift=True)))
    assert panel.selected_index == 0
    menu._handle_event(InputEvent(KeyBinding("down")))
    assert panel.selected_index == 1
    menu._handle_event(InputEvent(KeyBinding(" ", shift=True)))
    menu._handle_event(InputEvent(KeyBinding(" ", shift=True)))
    assert not playback.finished
    assert len(panel.content._selectable_items()) == 2
    assert_locked()


def test_turn_page_auto_advances_without_selecting_during_run() -> None:
    application = run("one_shot")
    menu = application.main_menu
    panel = application.simulation_panel
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


def test_rows_cannot_be_selected_during_one_shot() -> None:
    application = run("one_shot")
    menu = application.main_menu
    panel = application.simulation_panel
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
    panel = application.simulation_panel
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
    panel = application.simulation_panel
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


def test_selected_movement_shows_zone_details_and_resets() -> None:
    application = run("one_shot")
    playback = application.playback
    panel = application.simulation_panel
    assert playback is not None and panel is not None
    tick(application, 0)
    tick(application, 10)
    panel.select_item(0)
    details = application.movement_panel
    assert details is not None
    lines = details.content._static_value()
    assert "Drone: D-2" in lines
    assert "Zone: goal" in lines
    assert "  color: red" in lines
    assert "  zone_type: normal" in lines
    assert "  max_drones: 1" in lines
    assert "Other drones: D-1" in lines
    assert [row.panels for row in application.main_menu.content_layout] == [
        (application.graph_panel, panel),
        (application.graph_panel, details),
        (application.graph_panel, application.stats_panel),
    ]
    panel.clear_selection()
    assert application.movement_panel is None
    assert len(application.main_menu.content_panels) == 3
    panel.select_item(0)
    command = next(
        item for item in application.main_menu.commands
        if item.label == "Run simulation"
    )
    command.callback(CommandContext(
        application.terminal_app, application.main_menu, command, None
    ))
    assert application.movement_panel is None
    assert len(application.main_menu.content_panels) == 3


def test_connection_details_use_replayed_occupancy() -> None:
    application = run("one_shot")
    assert application.graph is not None
    panel = application.simulation_panel
    assert panel is not None
    graph = application.graph
    graph.connections[0].metadata.max_link_capacity = 2
    turns = [Turn(1, [
        Movement(1, "start-waypoint1"),
        Movement(2, "start-waypoint1"),
    ])]
    playback = Playback(graph, turns, "one_shot", 1)
    playback.advance(0)
    playback.advance(1)
    application.playback = playback
    panel.set_content(ScreenContent.selectable([
        SelectableItem("D-1-start-waypoint1", value=1),
        SelectableItem("D-2-start-waypoint1", value=2),
    ]))
    panel.clear_selection()
    panel.select_item(0)
    details = application.movement_panel
    assert details is not None
    assert "Connection: start-waypoint1" in details.content._static_value()
    assert "  max_link_capacity: 2" in details.content._static_value()
    assert not any(
        line.startswith("Other drones:")
        for line in details.content._static_value()
    )
    panel.clear_selection()
    panel.select_item(1)
    details = application.movement_panel
    assert details is not None
    assert "Other drones: D-1" in details.content._static_value()
