from __future__ import annotations

from typing import TYPE_CHECKING

from tuiloom import (
    AnimationFrame,
    CommandContext,
    KeyBinding,
    MenuDisplay,
    PanelCommandContext,
    ScreenContent,
    SelectableItem,
    SelectionChangeContext,
    StatusBar,
    style,
    TerminalMenu,
    display_width,
)

from src.simulation.playback import Playback
from src.simulation.simulator import Simulator
from src.ui.menus.settings_menu import build_settings_menu

if TYPE_CHECKING:
    from src.application import Application


def build_main_menu(application: Application) -> TerminalMenu:
    menu = TerminalMenu(
        application.terminal_app,
        MenuDisplay(
            menu_name="main",
            title="Main Menu",
            width=40,
        ),
        presentation="overlay",
    )

    application.terminal_app.add_global_command(
        KeyBinding("m"), "M", lambda context: menu.toggle_menu()
    )
    application.terminal_app.add_global_command(
        KeyBinding("M"), "M", lambda context: menu.toggle_menu()
    )

    shown_turn_index = 0

    def update_layout() -> None:
        graph = application.graph_panel
        output = application.simulation_panel
        stats = application.stats_panel
        if graph is None or output is None or stats is None:
            return
        layout = [[graph, output]]
        if application.movement_panel is not None:
            layout.append([graph, application.movement_panel])
        layout.append([graph, stats])
        menu.set_content_layout(layout)

    def clear_movement_panel() -> None:
        if application.movement_panel is not None:
            application.movement_panel.remove()
            application.movement_panel = None
            update_layout()

    def update_movement_panel(playback: Playback) -> None:
        snapshot = playback.snapshot()
        drone_id = snapshot.selected_drone_id
        if drone_id is None:
            clear_movement_panel()
            return
        visual = snapshot.positions[drone_id]
        location = visual.end if visual.progress == 1 else visual.start
        lines = [f"Drone: D-{drone_id}"]
        if location.zone is not None:
            zone = playback.graph.zones[location.zone]
            lines.append(f"Zone: {zone.name}")
            metadata = zone.metadata.model_dump()
        else:
            connection = next(
                connection for connection in playback.graph.connections
                if f"{connection.zone_name1}-{connection.zone_name2}"
                == location.connection
            )
            lines.append(f"Connection: {location.connection}")
            lines.append(f"Direction: {location.source} → {location.target}")
            metadata = connection.metadata.model_dump()
        lines.append("Metadata:")
        lines.extend(
            f"{'╰─' if index == len(metadata) - 1 else '├─'} "
            f"{key}: {value if value is not None else 'None'}"
            for index, (key, value) in enumerate(metadata.items())
        )
        others = []
        for other_id, other_visual in snapshot.positions.items():
            if other_id == drone_id:
                continue
            other = (
                other_visual.end if other_visual.progress == 1
                else other_visual.start
            )
            if (
                location.zone is not None and other.zone == location.zone
                or location.connection is not None
                and other.connection == location.connection
            ):
                others.append(f"D-{other_id}")
        if others:
            lines.append(f"Other drones: {', '.join(others)}")
        content = ScreenContent.lines(lines)
        if application.movement_panel is None:
            application.movement_panel = menu.add_content_panel(
                content,
                description="Movement",
                width_weight=2,
                padding_top=1,
                padding_left=1,
                padding_right=1,
            )
            update_layout()
        else:
            application.movement_panel.set_content(content)

    def render_status(width: int) -> str:
        playback = application.playback
        if application.renderer is None:
            return "NO MAP │ Select a map │ [Esc] Quit"

        if playback is not None:
            snapshot = playback.snapshot()
            state = "DONE" if snapshot.finished else "RUNNING"
        else:
            simulator = application.simulator
            count = len(simulator.state.turns) if simulator is not None else 0
            state = "RUNNING" if count else "READY"

        focused = menu.focused_panel
        controls = ["[M] Menu"]
        if menu.content_panels:
            controls.append("[Tab] Focus")
        if (
            playback is not None
            and playback.mode == "step_by_step"
            and not playback.finished
            and focused in (
                application.graph_panel, application.simulation_panel
            )
        ):
            controls.insert(0, "[Backspace] Previous move")
            controls.insert(1, "[Space] Next move")
        if (
            playback is not None and playback.finished
            and focused is application.simulation_panel
        ):
            controls.insert(0, "[Shift+←/→] Turns")

        path = application.map_path
        map_name = f"{path.parent.name}/{path.name}" if path else "No map"
        full = (
            f" {state} │ Map: {map_name}"
            f" │ {' │ '.join(controls)} │ [Esc] Quit"
        )
        medium = f" {state} │ {' │ '.join(controls)} │ [Esc] Quit"
        compact = f"{' │ '.join(controls)} │ [Esc] Quit"
        for text in (full, medium):
            if display_width(text) <= width:
                return text
        return compact

    menu.set_status_bar(StatusBar.responsive(render_status))

    def turn_rows(playback: Playback) -> list[str | SelectableItem]:
        turn = playback.turns[shown_turn_index]
        current_index = playback.current_movement_index
        return [
            SelectableItem(
                f"D-{movement.drone_id}-{movement.destination}",
                value=movement.drone_id,
                key=movement.drone_id,
                enabled=playback.finished or (
                    playback.mode == "step_by_step"
                    and index == current_index
                ),
            )
            for index, movement in enumerate(turn.movements)
        ]

    def turn_title(playback: Playback) -> str:
        turn = playback.turns[shown_turn_index]
        return style(f"Turn {turn.number}:", bold=True)

    def stats_lines(playback: Playback) -> list[str]:
        snapshot = playback.snapshot()
        delivered = sum(
            visual.end.zone == playback.graph.end_hub.name
            and visual.progress == 1
            for visual in snapshot.positions.values()
        )
        current = playback.turns[playback.turn_index]
        lines = [
            f"Current turn: {playback.turn_index + 1}/{len(playback.turns)}",
            f"╰─ Number of movements: {len(current.movements)}",
            f"Drones delivered: {delivered}/{playback.graph.nb_drones}",
        ]
        if snapshot.finished:
            arrivals = [
                turn.number
                for turn in playback.turns
                for move in turn.movements
                if move.destination == playback.graph.end_hub.name
            ]
            average = sum(arrivals) / len(arrivals) if arrivals else 0.0
            lines.extend([
                "\n",
                f"Average turns per drone: {average:.1f}",
                f"Total path cost: {sum(len(turn.movements)
                                        for turn in playback.turns)}",
            ])
        return lines

    def update_turn_panel(
        playback: Playback, *, select_first: bool = False
    ) -> None:
        panel = application.simulation_panel
        if panel is None:
            return
        panel.set_selection_callback(None)
        panel.set_header(turn_title(playback))
        panel.set_content(ScreenContent.selectable(turn_rows(playback)))
        panel.clear_selection()
        panel.set_selection_callback(on_selection_change)
        playback.clear_replay()
        clear_movement_panel()
        if select_first:
            panel.select_item(0)

    def update_stats_panel(playback: Playback) -> None:
        if application.stats_panel is not None:
            application.stats_panel.set_content(
                ScreenContent.lines(stats_lines(playback))
            )

    def on_selection_change(context: SelectionChangeContext) -> None:
        playback = application.playback
        if playback is None:
            return
        if context.index is None:
            playback.clear_replay()
        elif playback.finished:
            playback.select_movement(shown_turn_index, context.index)
        else:
            movement = playback.turns[shown_turn_index].movements[
                context.index
            ]
            playback.select_drone(movement.drone_id)
        update_movement_panel(playback)

    def change_turn(context: PanelCommandContext, step: int) -> None:
        nonlocal shown_turn_index
        playback = application.playback
        if playback is None or not playback.finished:
            return
        next_index = max(
            0, min(shown_turn_index + step, len(playback.turns) - 1)
        )
        if next_index != shown_turn_index:
            shown_turn_index = next_index
            update_turn_panel(playback, select_first=True)
            menu.refresh_status_bar()

    def start_step(context: PanelCommandContext) -> None:
        playback = application.playback
        if playback is not None and playback.start_next_movement():
            sync_step_selection(playback)
            context.menu.refresh_status_bar()

    def sync_step_selection(playback: Playback) -> None:
        nonlocal shown_turn_index
        panel = application.simulation_panel
        if panel is None or not playback.turns:
            return
        if shown_turn_index != playback.turn_index:
            shown_turn_index = playback.turn_index
            update_turn_panel(playback)
        index = playback.current_movement_index
        # Automatic selection follows live playback, including the final row.
        # It must not invoke the historical replay callback when finished.
        panel.set_selection_callback(None)
        panel.set_content(ScreenContent.selectable(turn_rows(playback)))
        panel.select_item(index)
        panel.set_selection_callback(on_selection_change)
        playback.clear_replay()
        playback.select_drone(playback.turns[shown_turn_index].movements[
            index
        ].drone_id)
        update_movement_panel(playback)

    def previous_step(context: CommandContext) -> None:
        playback = application.playback
        if playback is not None and playback.previous_movement():
            sync_step_selection(playback)
            update_stats_panel(playback)
            menu.refresh_status_bar()

    application.terminal_app.add_global_command(
        KeyBinding("backspace"), "Previous move", previous_step,
    )

    def run_simulation(context: CommandContext) -> None:
        nonlocal shown_turn_index
        renderer = application.renderer
        if renderer is None:
            return
        try:
            simulator = Simulator(
                renderer.graph, routing_mode=application.drones_routing_mode
            )
            simulator.simulate()
        except RuntimeError as error:
            context.menu.show_alert(str(error))
            return

        if application.playback_tick is not None:
            application.playback_tick.cancel()
        application.simulator = simulator
        playback = Playback(
            renderer.graph, simulator.state.turns,
            application.simulation_mode, application.seconds_per_movement,
        )
        application.playback = playback
        clear_movement_panel()
        shown_turn_index = 0
        context.menu.hide_menu()

        graph_content = ScreenContent.animated(
            lambda size, frame: renderer.render(
                size, frame, playback.snapshot()
            ),
            fps=20,
            min_width=40,
            min_height=20,
        )
        if application.graph_panel is None:
            application.graph_panel = context.menu.add_content_panel(
                graph_content,
                description="Graph",
                width_weight=3,
                padding_top=1,
                padding_bottom=1,
                padding_left=1,
                padding_right=1
            )
        else:
            application.graph_panel.set_content(graph_content)

        output_content = ScreenContent.selectable(turn_rows(playback))
        if application.simulation_panel is None:
            application.simulation_panel = context.menu.add_content_panel(
                output_content,
                description="Simulation",
                height_weight=2,
                width_weight=2,
                selection_style="reverse",
                header=turn_title(playback),
                padding_top=1,
                padding_left=1,
                padding_right=1
            )
        else:
            application.simulation_panel.set_selection_callback(None)
            application.simulation_panel.set_header(turn_title(playback))
            application.simulation_panel.set_content(output_content)
        application.simulation_panel.clear_selection()
        application.simulation_panel.set_selection_callback(
            on_selection_change
        )

        stats_content = ScreenContent.lines(stats_lines(playback))
        if application.stats_panel is None:
            application.stats_panel = context.menu.add_content_panel(
                stats_content,
                description="Stats",
                padding_top=1,
                padding_left=1,
                padding_right=1
            )
        else:
            application.stats_panel.set_content(stats_content)

        for panel in (application.graph_panel, application.simulation_panel):
            for command in panel.key_commands:
                panel.remove_key_command(command)
        if playback.mode == "step_by_step":
            for panel in (
                application.graph_panel, application.simulation_panel
            ):
                panel.add_key_command(
                    KeyBinding(" "), "Next move", start_step
                )
        application.simulation_panel.add_key_command(
            KeyBinding("left", shift=True), "Previous turn",
            lambda panel_context: change_turn(panel_context, -1),
        )
        application.simulation_panel.add_key_command(
            KeyBinding("right", shift=True), "Next turn",
            lambda panel_context: change_turn(panel_context, 1),
        )
        update_layout()
        if playback.mode == "step_by_step":
            sync_step_selection(playback)

        last_completed = 0

        def on_tick(frame: AnimationFrame) -> None:
            nonlocal shown_turn_index, last_completed
            was_finished = playback.finished
            page_changed = playback.advance(frame.elapsed)
            just_finished = playback.finished and not was_finished
            if page_changed or just_finished:
                shown_turn_index = playback.turn_index
                update_turn_panel(playback)
            if (
                page_changed or just_finished
                or playback.completed_movements != last_completed
            ):
                last_completed = playback.completed_movements
                if playback.mode == "step_by_step":
                    sync_step_selection(playback)
                update_stats_panel(playback)
                if application.movement_panel is not None:
                    update_movement_panel(playback)
                context.menu.refresh_status_bar()

        application.playback_tick = context.menu.add_tick_callback(
            on_tick, fps=20
        )
        context.menu.refresh_status_bar()

    def credit(context: CommandContext) -> None:
        context.menu.toggle_message("credit")

    menu.add_command(label="Run simulation", callback=run_simulation)
    menu.add_submenu(
        submenu=build_settings_menu(application), label="Settings"
    )
    menu.add_command(label="Credit", callback=credit)
    return menu
