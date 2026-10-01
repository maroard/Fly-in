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
            focused is application.output_panel
            and playback is not None
            and playback.finished
        ):
            controls.insert(0, "[↑/↓] Locate")
        if (
            playback is not None
            and playback.mode == "step_by_step"
            and not playback.finished
            and focused in (application.graph_panel, application.output_panel)
        ):
            controls.insert(0, "[Space] Next move")
        if (
            playback is not None and playback.finished
            and focused is application.output_panel
        ):
            controls.insert(0, "[Shift+←/→] Turns")

        path = application.map_path
        map_name = f"{path.parent.name}/{path.name}" if path else "No map"
        full = (
            f" {state} │ Map: {map_name}"
            f" │ {' │ '.join(controls)} │ [Esc] Quit"
        )
        compact = f" {state} │ {' │ '.join(controls)} │ [Esc] Quit"
        if display_width(full) <= width:
            return full
        return compact

    menu.set_status_bar(StatusBar.responsive(render_status))

    def turn_rows(playback: Playback) -> list[str | SelectableItem]:
        turn = playback.turns[shown_turn_index]
        return [
            SelectableItem(
                f"D-{movement.drone_id}-{movement.destination}",
                value=movement.drone_id,
                key=movement.drone_id,
                enabled=playback.finished,
            )
            for movement in turn.movements
        ]

    def turn_title(playback: Playback) -> str:
        turn = playback.turns[shown_turn_index]
        return style(f"Turn {turn.number}:", bold=True)

    def info_lines(playback: Playback) -> list[str]:
        snapshot = playback.snapshot()
        delivered = sum(
            visual.end.zone == playback.graph.end_hub.name
            and visual.progress == 1
            for visual in snapshot.positions.values()
        )
        previous = sum(
            len(turn.movements)
            for turn in playback.turns[:playback.turn_index]
        )
        moved_this_turn = snapshot.completed_movements - previous
        current = playback.turns[playback.turn_index]
        lines = [
            f"Turn: {playback.turn_index + 1}/{len(playback.turns)}",
            f"Delivered: {delivered}/{playback.graph.nb_drones}",
            f"Movements: {moved_this_turn}/{len(current.movements)}",
            f"Total: {len(playback.turns)}t",
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
                f"Average turns per drone: {average:.1f}t",
                f"Total path cost: {sum(len(turn.movements)
                                        for turn in playback.turns)}",
            ])
        return lines

    def update_turn_panel(
        playback: Playback, *, select_first: bool = False
    ) -> None:
        panel = application.output_panel
        if panel is None:
            return
        panel.set_selection_callback(None)
        panel.set_header(turn_title(playback))
        panel.set_content(ScreenContent.selectable(turn_rows(playback)))
        if playback.finished:
            panel.clear_selection()
        panel.set_selection_callback(on_selection_change)
        playback.clear_replay()
        if select_first:
            panel.select_item(0)

    def update_info_panel(playback: Playback) -> None:
        if application.info_panel is not None:
            application.info_panel.set_content(
                ScreenContent.lines(info_lines(playback))
            )

    def on_selection_change(context: SelectionChangeContext) -> None:
        playback = application.playback
        if playback is None or not playback.finished:
            return
        if context.index is None:
            playback.clear_replay()
        else:
            playback.select_movement(shown_turn_index, context.index)

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
            context.menu.refresh_status_bar()

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
                graph_content, description="Graph", width_weight=3,
            )
        else:
            application.graph_panel.set_content(graph_content)

        output_content = ScreenContent.selectable(turn_rows(playback))
        if application.output_panel is None:
            application.output_panel = context.menu.add_content_panel(
                output_content, description="Simulation", width_weight=2,
                selection_style="reverse", header=turn_title(playback),
            )
        else:
            application.output_panel.set_selection_callback(None)
            application.output_panel.set_header(turn_title(playback))
            application.output_panel.set_content(output_content)
        application.output_panel.set_selection_callback(on_selection_change)

        info_content = ScreenContent.lines(info_lines(playback))
        if application.info_panel is None:
            application.info_panel = context.menu.add_content_panel(
                info_content, description="Info", width_weight=1,
            )
        else:
            application.info_panel.set_content(info_content)

        for panel in (application.graph_panel, application.output_panel):
            for command in panel.key_commands:
                panel.remove_key_command(command)
        if playback.mode == "step_by_step":
            for panel in (application.graph_panel, application.output_panel):
                panel.add_key_command(
                    KeyBinding(" "), "Next move", start_step
                )
        application.output_panel.add_key_command(
            KeyBinding("left", shift=True), "Previous turn",
            lambda panel_context: change_turn(panel_context, -1),
        )
        application.output_panel.add_key_command(
            KeyBinding("right", shift=True), "Next turn",
            lambda panel_context: change_turn(panel_context, 1),
        )
        context.menu.set_content_layout([
            [application.graph_panel, application.output_panel],
            [application.graph_panel, application.info_panel],
        ])

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
                update_info_panel(playback)
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
