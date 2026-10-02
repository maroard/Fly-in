"""Control simulation playback panels, selections and result export."""

from __future__ import annotations

from pathlib import Path
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
from src.ui.menus.settings_menu import SettingsMenu

if TYPE_CHECKING:
    from src.application import Application


class MainMenu:
    """Own the main menu callbacks and playback display state.

    Attributes:
        application: Shared application data and panel handles.
        menu: Terminal menu with callbacks bound to this instance.
        shown_turn_index: Zero-based index of the displayed live or
            historical turn.
        last_completed: Completed-movement count at the previous UI
            refresh.
    """

    @classmethod
    def build(cls, application: Application) -> TerminalMenu:
        """Create a Tuiloom menu backed by a MainMenu instance.

        Args:
            application: Shared application state used by the menu or test
                helper.

        Returns:
            Main terminal menu with callbacks bound to its owner.
        """
        return cls(application).menu

    def __init__(self, application: Application) -> None:
        """Create the menu and register its commands.

        Args:
            application: Shared application state used by the menu or test
                helper.
        """
        self.application = application

        self.menu = TerminalMenu(
            self.application.terminal_app,
            MenuDisplay(
                menu_name="main",
                title="Main Menu",
                width=40,
            ),
            presentation="overlay",
        )

        self.shown_turn_index = 0
        self.last_completed = 0

        self.application.terminal_app.add_global_command(
            KeyBinding("m"),
            "M",
            self.toggle_menu
        )

        self.application.terminal_app.add_global_command(
            KeyBinding("M"),
            "M",
            self.toggle_menu
        )

        self.menu.set_status_bar(StatusBar.responsive(self.render_status))

        self.menu.add_command(
            label="Run simulation",
            callback=self.run_simulation
        )

        self.menu.add_submenu(
            submenu=SettingsMenu.build(self.application),
            label="Settings"
        )

        self.menu.add_command(
            label="Credit",
            callback=self.credit
        )

    def toggle_menu(self, context: CommandContext) -> None:
        """Toggle the main menu overlay.

        Args:
            context: Tuiloom command context containing the application and
                menu.
        """
        self.menu.toggle_menu()

    def update_layout(self) -> None:
        """Place the graph beside simulation, movement details and stats."""
        graph = self.application.graph_panel
        simulation = self.application.simulation_panel
        stats = self.application.stats_panel

        if graph is None or simulation is None or stats is None:
            return

        layout = [[graph, simulation]]

        if self.application.movement_panel is not None:
            layout.append([graph, self.application.movement_panel])

        layout.append([graph, stats])

        self.menu.set_content_layout(layout)

    def clear_movement_panel(self) -> None:
        """Remove movement details when no movement is selected."""
        if self.application.movement_panel is not None:
            self.application.movement_panel.remove()
            self.application.movement_panel = None

            self.update_layout()

    def update_movement_panel(self, playback: Playback) -> None:
        """Show the selected drone, its location and nearby drones.

        Args:
            playback: Playback whose recorded turns or visible state are
                displayed.
        """
        snapshot = playback.snapshot()
        drone_id = snapshot.selected_drone_id

        if drone_id is None:
            self.clear_movement_panel()
            return

        visual = snapshot.positions[drone_id]
        location = visual.end if visual.progress == 1 else visual.start
        lines = [f"Drone: D{drone_id}"]

        if location.zone is not None:
            zone = playback.graph.zones[location.zone]
            lines.append(f"Zone: {zone.name}")

            metadata = zone.metadata.model_dump()
        else:
            connection = next(
                connection
                for connection in playback.graph.connections
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
                other_visual.end
                if other_visual.progress == 1
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

        if self.application.movement_panel is None:
            self.application.movement_panel = self.menu.add_content_panel(
                content,
                description="Movement",
                width_weight=2,
                padding_top=1,
                padding_left=1,
                padding_right=1,
            )

            self.update_layout()
        else:
            self.application.movement_panel.set_content(content)

    def render_status(self, width: int) -> str:
        """Format the state and keyboard hints for the available width.

        Args:
            width: Available width in terminal columns.

        Returns:
            Status and keyboard hints adapted to the available width.
        """
        playback = self.application.playback

        if self.application.renderer is None:
            return "NO MAP │ Select a map │ [Esc] Quit"

        if playback is not None:
            snapshot = playback.snapshot()
            state = "DONE" if snapshot.finished else "RUNNING"
        else:
            simulator = self.application.simulator
            count = len(simulator.state.turns) if simulator is not None else 0
            state = "RUNNING" if count else "READY"

        focused = self.menu.focused_panel
        controls = ["[M] Menu"]

        if self.menu.content_panels:
            controls.append("[Tab] Focus")

        if (
            playback is not None
            and playback.mode == "step_by_step"
            and not playback.finished
            and focused in (
                self.application.graph_panel,
                self.application.simulation_panel,
            )
        ):
            controls.insert(0, "[Backspace] Previous move")
            controls.insert(1, "[Space] Next move")

        if (
            playback is not None
            and playback.finished
            and focused is self.application.simulation_panel
        ):
            controls.insert(0, "[Shift+←/→] Turns")

        path = self.application.map_path
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

    def turn_rows(self, playback: Playback) -> list[str | SelectableItem]:
        """Build movement rows with the current selection restrictions.

        Args:
            playback: Playback whose recorded turns or visible state are
                displayed.

        Returns:
            Movement items enabled according to playback mode and
            completion.
        """
        turn = playback.turns[self.shown_turn_index]
        current_index = playback.current_movement_index

        return [
            SelectableItem(
                f"D{movement.drone_id}-{movement.destination}",
                value=movement.drone_id,
                key=movement.drone_id,
                enabled=playback.finished or (
                    playback.mode == "step_by_step"
                    and index == current_index
                ),
            )
            for index, movement in enumerate(turn.movements)
        ]

    def turn_title(self, playback: Playback) -> str:
        """Format the heading of the displayed turn.

        Args:
            playback: Playback whose recorded turns or visible state are
                displayed.

        Returns:
            Bold heading containing the displayed simulation turn number.
        """
        turn = playback.turns[self.shown_turn_index]

        return style(f"Turn {turn.number}:", bold=True)

    def stats_lines(self, playback: Playback) -> list[str]:
        """Summarize playback progress and final results.

        Args:
            playback: Playback whose recorded turns or visible state are
                displayed.

        Returns:
            Progress lines and, after completion, aggregate result lines.
        """
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

            lines.extend(
                [
                    "\n",
                    f"Average turns per drone: {average:.1f}",
                    f"Total path cost: {sum(
                        len(turn.movements)
                        for turn in playback.turns
                    )}",
                ]
            )

        return lines

    def update_turn_panel(
        self,
        playback: Playback,
        *,
        select_first: bool = False,
    ) -> None:
        """Replace the displayed turn and optionally select its first row.

        Args:
            playback: Playback whose recorded turns or visible state are
                displayed.
            select_first: Whether to select the first movement after
                replacing the panel.
        """
        panel = self.application.simulation_panel

        if panel is None:
            return

        panel.set_selection_callback(None)
        panel.set_header(self.turn_title(playback))
        panel.set_content(
            ScreenContent.selectable(self.turn_rows(playback))
        )

        panel.clear_selection()
        panel.set_selection_callback(self.on_selection_change)

        playback.clear_replay()
        self.clear_movement_panel()

        if select_first:
            panel.select_item(0)

    def update_stats_panel(self, playback: Playback) -> None:
        """Refresh the simulation statistics.

        Args:
            playback: Playback whose recorded turns or visible state are
                displayed.
        """
        if self.application.stats_panel is not None:
            self.application.stats_panel.set_content(
                ScreenContent.lines(self.stats_lines(playback))
            )

    def on_selection_change(self, context: SelectionChangeContext) -> None:
        """Highlight a live drone or replay a completed movement.

        Args:
            context: Tuiloom callback context containing the selected
                movement row.
        """
        playback = self.application.playback

        if playback is None:
            return

        if context.index is None:
            playback.clear_replay()
        elif playback.finished:
            playback.select_movement(self.shown_turn_index, context.index)
        else:
            movement = playback.turns[self.shown_turn_index].movements[
                context.index
            ]
            playback.select_drone(movement.drone_id)

        self.update_movement_panel(playback)

    def change_turn(self, context: PanelCommandContext, step: int) -> None:
        """Browse historical turns after playback finishes.

        Args:
            context: Tuiloom command context for the focused content panel.
            step: Signed offset from the displayed turn, usually -1 or 1.
        """
        playback = self.application.playback

        if playback is None or not playback.finished:
            return

        next_index = max(
            0,
            min(self.shown_turn_index + step, len(playback.turns) - 1)
        )

        if next_index != self.shown_turn_index:
            self.shown_turn_index = next_index
            self.update_turn_panel(playback, select_first=True)
            self.menu.refresh_status_bar()

    def next_step(self, context: PanelCommandContext) -> None:
        """Start the waiting movement and synchronize its selection.

        Args:
            context: Tuiloom command context for the focused content panel.
        """
        playback = self.application.playback

        if playback is not None and playback.start_next_movement():
            self.sync_step_selection(playback)
            self.update_stats_panel(playback)
            context.menu.refresh_status_bar()

    def previous_step(self, context: PanelCommandContext) -> None:
        """Undo a movement and refresh the panels.

        Args:
            context: Tuiloom command context for the focused content panel.
        """
        playback = self.application.playback

        if playback is not None and playback.previous_movement():
            self.sync_step_selection(playback)
            self.update_stats_panel(playback)
            context.menu.refresh_status_bar()

    def sync_step_selection(self, playback: Playback) -> None:
        """Select the active or waiting movement in live playback.

        Args:
            playback: Playback whose recorded turns or visible state are
                displayed.
        """
        panel = self.application.simulation_panel

        if panel is None or not playback.turns:
            return

        if self.shown_turn_index != playback.turn_index:
            self.shown_turn_index = playback.turn_index
            self.update_turn_panel(playback)

        index = playback.current_movement_index

        panel.set_selection_callback(None)
        panel.set_content(
            ScreenContent.selectable(self.turn_rows(playback))
        )
        panel.select_item(index)
        panel.set_selection_callback(self.on_selection_change)

        playback.clear_replay()
        playback.select_drone(
            playback.turns[self.shown_turn_index].movements[index].drone_id
        )

        self.update_movement_panel(playback)

    def run_simulation(self, context: CommandContext) -> None:
        """Calculate a simulation and install its panels and playback.

        Args:
            context: Tuiloom command context containing the application and
                menu.
        """
        application = self.application
        renderer = application.renderer

        if renderer is None:
            return

        try:
            simulator = Simulator(
                renderer.graph,
                routing_mode=application.drones_routing_mode
            )

            simulator.simulate()
        except RuntimeError as error:
            context.menu.display_state.message = str(error)
            context.menu.show_menu()
            return

        context.menu.clear_message()

        if application.playback_tick is not None:
            application.playback_tick.cancel()

        application.simulator = simulator

        playback = Playback(
            renderer.graph,
            simulator.state.turns,
            application.simulation_mode,
            application.seconds_per_movement,
        )
        application.playback = playback

        self.clear_movement_panel()
        self.shown_turn_index = 0

        context.menu.hide_menu()

        graph_content = ScreenContent.animated(
            lambda size, frame: renderer.render(
                size,
                frame,
                playback.snapshot()
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

        simulation_content = ScreenContent.selectable(self.turn_rows(playback))

        if application.simulation_panel is None:
            application.simulation_panel = context.menu.add_content_panel(
                simulation_content,
                description="Simulation",
                height_weight=2,
                width_weight=2,
                selection_style="reverse",
                header=self.turn_title(playback),
                padding_top=1,
                padding_left=1,
                padding_right=1
            )
        else:
            application.simulation_panel.set_selection_callback(None)
            application.simulation_panel.set_header(self.turn_title(playback))
            application.simulation_panel.set_content(simulation_content)

        application.simulation_panel.clear_selection()
        application.simulation_panel.set_selection_callback(
            self.on_selection_change
        )

        stats_content = ScreenContent.lines(self.stats_lines(playback))

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
                panel.add_key_command(
                    KeyBinding(" "),
                    "Next move",
                    self.next_step
                )

                panel.add_key_command(
                    KeyBinding("Backspace"),
                    "Previous move",
                    self.previous_step
                )

        application.simulation_panel.add_key_command(
            KeyBinding("left", shift=True),
            "Previous turn",
            lambda panel_context: self.change_turn(panel_context, -1),
        )

        application.simulation_panel.add_key_command(
            KeyBinding("right", shift=True),
            "Next turn",
            lambda panel_context: self.change_turn(panel_context, 1),
        )

        self.update_layout()

        if playback.mode == "step_by_step":
            self.sync_step_selection(playback)

        self.last_completed = 0

        application.playback_tick = context.menu.add_tick_callback(
            self.on_tick,
            fps=20
        )

        context.menu.refresh_status_bar()

    def on_tick(self, frame: AnimationFrame) -> None:
        """Advance playback and synchronize the displayed state.

        Args:
            frame: Tick timing used to advance playback.
        """
        playback = self.application.playback

        if playback is None:
            return

        was_finished = playback.finished
        page_changed = playback.advance(frame.elapsed)

        just_finished = playback.finished and not was_finished

        if just_finished:
            self.save_output(playback)

        if page_changed or just_finished:
            self.shown_turn_index = playback.turn_index
            self.update_turn_panel(playback)

        if (
            page_changed
            or just_finished
            or playback.completed_movements != self.last_completed
        ):
            self.last_completed = playback.completed_movements

            if playback.mode == "step_by_step":
                self.sync_step_selection(playback)

            self.update_stats_panel(playback)

            if self.application.movement_panel is not None:
                self.update_movement_panel(playback)

            self.menu.refresh_status_bar()

    def save_output(self, playback: Playback) -> None:
        """Write completed turns to output.txt at the project root.

        Write one space-separated movement line per turn. Replace the
        previous result and report write errors in the menu.

        Args:
            playback: Playback whose recorded turns or visible state are
                displayed.
        """
        path = Path(__file__).resolve().parents[3] / "output.txt"

        try:
            with path.open("w", encoding="utf-8") as output:
                for turn in playback.turns:
                    line = " ".join(
                        f"D{movement.drone_id}-{movement.destination}"
                        for movement in turn.movements
                    )

                    output.write(f"{line}\n")
        except OSError as error:
            self.menu.display_state.message = (
                f"Could not write output.txt: {error}"
            )
            self.menu.show_menu()

    def credit(self, context: CommandContext) -> None:
        """Toggle the project credit message.

        Args:
            context: Tuiloom command context containing the application and
                menu.
        """
        context.menu.toggle_message("credit")
