from pathlib import Path

import pytest
from tuiloom import AnimationFrame, CommandContext, MenuChoice, TerminalMenu
from tuiloom.render.menu_renderer import MenuRenderer
from tuiloom.render.terminal_renderer import TerminalRenderer

from src.application import Application
from src.ui.menus.map_menu import build_map_menu


def activate(menu: TerminalMenu, label: str) -> None:
    command = next(
        command for command in menu.commands if command.label == label
    )
    command.callback(CommandContext(menu.app, menu, command, None))


def select_map(menu: TerminalMenu, category: str, filename: str) -> None:
    choice = next(
        command for command in menu.commands if command.label == category
    )
    assert isinstance(choice, MenuChoice)
    index = next(
        index for index, option in enumerate(choice.options)
        if option.label == filename
    )
    menu.set_choice_index(choice, index)
    choice.callback(CommandContext(menu.app, menu, choice, None))


def test_initial_map_selection_and_later_map_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application = Application()
    entry_menus: list[TerminalMenu] = []
    monkeypatch.setattr(
        application.terminal_app,
        "run",
        lambda entry_menu=None: entry_menus.append(entry_menu),
    )

    application.run()

    assert len(entry_menus) == 1
    map_menu = entry_menus[0]
    assert application.main_menu is not map_menu
    assert "Settings" in [
        command.label for command in application.main_menu.commands
    ]
    main_text = application.main_menu.display_state.text
    assert main_text is not None
    assert "No map selected" in main_text

    application.terminal_app.push_menu(map_menu)
    select_map(map_menu, "Easy", "01_linear_path.txt")
    assert application.map_path == Path("maps/easy/01_linear_path.txt")
    main_text = application.main_menu.display_state.text
    assert main_text is not None
    assert "easy/01_linear_path.txt" in main_text
    assert application.terminal_app._menu_stack == [application.main_menu]

    activate(application.main_menu, "Run simulation")
    assert len(application.main_menu.content_panels) == 3
    assert application.simulator is not None

    activate(application.main_menu, "Settings")
    settings_menu = application.terminal_app._menu_stack[-1]
    activate(settings_menu, "Change map")
    map_menu = application.terminal_app._menu_stack[-1]
    select_map(map_menu, "Medium", "01_dead_end_trap.txt")
    assert application.map_path == Path("maps/medium/01_dead_end_trap.txt")
    main_text = application.main_menu.display_state.text
    assert main_text is not None
    assert "medium/01_dead_end_trap.txt" in main_text
    assert application.terminal_app._menu_stack == [application.main_menu]
    assert application.simulator is None
    assert application.main_menu.content_panels == ()


def test_category_choice_selects_a_later_map_without_submenu() -> None:
    application = Application()
    map_menu = build_map_menu(application)
    application.terminal_app.push_menu(map_menu)

    select_map(map_menu, "Easy", "02_simple_fork.txt")

    assert application.map_path == Path("maps/easy/02_simple_fork.txt")
    assert application.terminal_app._menu_stack == [application.main_menu]


def test_routing_mode_change_restarts_simulation() -> None:
    application = Application()
    map_menu = build_map_menu(application)
    application.terminal_app.push_menu(map_menu)
    select_map(map_menu, "Easy", "02_simple_fork.txt")

    activate(application.main_menu, "Run simulation")
    first = application.simulator
    assert first is not None
    assert first.mode == "single-path"
    assert len(first.state.turns) == 6

    activate(application.main_menu, "Settings")
    settings = application.terminal_app._menu_stack[-1]
    routing_choice = next(
        choice for choice in settings.commands
        if choice.label == "Drones routing mode"
    )
    assert isinstance(routing_choice, MenuChoice)
    settings.set_choice_index(routing_choice, 1)
    routing_choice.callback(CommandContext(
        settings.app, settings, routing_choice, None
    ))
    assert application.drones_routing_mode == "multi-path"

    activate(application.main_menu, "Run simulation")
    second = application.simulator
    assert second is not None
    assert second is not first
    assert second.mode == "multi-path"
    assert len(second.state.turns) == 5
    assert any(
        movement.destination == "path_b"
        for turn in second.state.turns
        for movement in turn.movements
    )


def test_reopened_map_menu_marks_only_the_active_map() -> None:
    application = Application()
    initial = build_map_menu(application)
    assert all(
        isinstance(choice, MenuChoice) and choice.selected_index is None
        for choice in initial.commands
    )

    application.terminal_app.push_menu(initial)
    select_map(initial, "Easy", "02_simple_fork.txt")
    activate(application.main_menu, "Settings")
    settings = application.terminal_app._menu_stack[-1]
    activate(settings, "Change map")
    reopened = application.terminal_app._menu_stack[-1]

    easy = next(
        choice for choice in reopened.commands if choice.label == "Easy"
    )
    assert isinstance(easy, MenuChoice)
    assert easy.selected_label == "02_simple_fork.txt"
    reopened._selected_index = easy.position
    assert "02_simple_fork.txt ✓" in MenuRenderer(reopened).render()
    assert all(
        choice.selected_index is None
        for choice in reopened.commands
        if choice is not easy and isinstance(choice, MenuChoice)
    )


def select_linear_map(application: Application) -> None:
    maps = build_map_menu(application)
    application.terminal_app.push_menu(maps)
    select_map(maps, "Easy", "01_linear_path.txt")


def test_repeated_simulations_reuse_three_panels_and_preserve_layout() -> None:
    application = Application()
    select_linear_map(application)
    activate(application.main_menu, "Run simulation")
    graph = application.graph_panel
    output = application.output_panel
    info = application.info_panel
    assert graph is not None and output is not None and info is not None
    assert graph.description == "Graph"
    assert output.description == "Simulation"
    assert graph.width_weight == 3
    assert output.width_weight == 2
    assert info.width_weight == 1

    graph.set_layout(width_weight=4, min_height=2)
    output.set_layout(width_weight=2, max_height=6)
    activate(application.main_menu, "Run simulation")

    assert application.graph_panel is graph
    assert application.output_panel is output
    assert application.info_panel is info
    assert application.main_menu.content_panels == (graph, output, info)
    assert (graph.width_weight, graph.min_height) == (4, 2)
    assert (output.width_weight, output.max_height) == (2, 6)


def test_panel_sizing_gives_graph_more_width_than_side_panels() -> None:
    application = Application()
    select_linear_map(application)
    activate(application.main_menu, "Run simulation")
    graph = application.graph_panel
    output = application.output_panel
    info = application.info_panel
    assert graph is not None and output is not None and info is not None
    menu = application.main_menu
    menu_renderer = MenuRenderer(menu)
    renderer = TerminalRenderer(
        menu=menu, menu_renderer=menu_renderer, content_spacing=True
    )
    assert menu.presentation == "overlay" and not menu.menu_visible
    # Overlay panels share the whole body: only the status row is reserved.
    frame = renderer._compose_frame(100, 26)

    assert graph._runtime.viewport is not None
    assert output._runtime.viewport is not None
    assert info._runtime.viewport is not None
    assert graph._runtime.viewport.width > output._runtime.viewport.width
    assert output._runtime.viewport.width > info._runtime.viewport.width
    assert graph._runtime.effective_size is not None
    assert graph._runtime.effective_size.height >= 20
    assert len(frame) == 26
    assert info.description == "Info"


def make_main_renderer(application: Application) -> TerminalRenderer:
    menu = application.main_menu
    return TerminalRenderer(
        menu=menu, menu_renderer=MenuRenderer(menu), content_spacing=True
    )


def test_status_tracks_map_simulation_and_reset_at_unchanged_width() -> None:
    application = Application()
    menu = application.main_menu
    renderer = make_main_renderer(application)
    assert menu.status_bar is not None
    assert renderer._compose_frame(120, 40)[-1].startswith("NO MAP")

    select_linear_map(application)
    ready = renderer._compose_frame(120, 40)[-1]
    assert ready.startswith("READY")
    assert "easy/01_linear_path.txt" in ready
    assert "Turn 0" in ready
    assert "0/2 delivered" in ready
    assert "[Tab]" not in ready
    assert menu.content_panels == ()

    activate(menu, "Run simulation")
    running = renderer._compose_frame(120, 40)[-1]
    assert running.startswith("RUNNING")
    assert "Turn 1/4" in running
    assert application.playback_tick is not None
    application.playback_tick.callback(AnimationFrame(0, 0))
    application.playback_tick.callback(AnimationFrame(4, 80))
    done = renderer._compose_frame(120, 40)[-1]
    assert done.startswith("DONE")
    assert "Turn 4/4" in done
    assert "2/2 delivered" in done
    assert "[Tab] Focus" in done
    assert len(menu.content_panels) == 3

    select_linear_map(application)
    assert renderer._compose_frame(120, 40)[-1] == ready
    assert application.simulator is None
    assert menu.content_panels == ()


def test_status_responsive_layout_and_explicit_refresh_example() -> None:
    from tuiloom import display_width
    from src.simulation.simulator import Simulator

    application = Application()
    select_linear_map(application)
    renderer = make_main_renderer(application)
    menu = application.main_menu
    assert application.renderer is not None
    simulator = Simulator(application.renderer.graph)
    application.simulator = simulator
    menu.refresh_status_bar()
    initial = renderer._compose_frame(120, 40)[-1]
    assert initial.startswith("READY")
    simulator.step()
    # Responsive values stay cached until a width change or explicit refresh.
    assert renderer._compose_frame(120, 40)[-1] == initial
    menu.refresh_status_bar()
    full = renderer._compose_frame(120, 40)[-1]
    assert full.startswith("RUNNING")
    assert "Turn 1" in full
    assert "0/2 delivered" in full
    medium = renderer._compose_frame(65, 40)[-1]
    assert "Map:" not in medium
    assert "Turn 1" in medium
    compact = renderer._compose_frame(42, 40)[-1]
    assert compact == "RUNNING │ T1 │ 0/2 │ [Esc] Quit"
    for width in (1, 25, 42, 65, 120):
        frame = renderer._compose_frame(width, 40)
        assert len(frame) in (1, 40)
        assert display_width(frame[-1]) <= width
