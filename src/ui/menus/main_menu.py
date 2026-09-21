from __future__ import annotations
from typing import TYPE_CHECKING

from tuiloom import CommandContext, ScreenContent, ScreenContext, TerminalMenu

if TYPE_CHECKING:
    from src.application import Application
from src.ui.menus.map_menu import build_map_menu
from src.output.formatter import format_turn


def build_main_menu(application: Application) -> TerminalMenu:
    menu = TerminalMenu(
        application.terminal_app,
        ScreenContext(
            menu_name="main",
            title="Main Menu",
            text="Current map: No map selected",
            width=40,
        ),
    )

    def run_simulation(context: CommandContext) -> None:
        if application.renderer is None:
            return

        application.graph_panel = context.menu.set_content(
            ScreenContent.responsive(
                application.renderer.render,
                min_width=40,
                min_height=20,
                refresh_mode="resize",
            ),
            description="Graph",
        )
        application.graph_panel.move(0)

        def render_turns() -> list[str]:
            if application.simulator is None:
                return []

            return [
                f"Tour {turn.number}: {format_turn(turn.movements)}"
                for turn in application.simulator.state.turns
            ]

        turns_content = ScreenContent.dynamic(render_turns)

        if application.output_panel is None:
            application.output_panel = context.menu.add_content_panel(
                turns_content,
                description="Simulation",
                position=1,
            )
        else:
            application.output_panel.set_content(turns_content)
            application.output_panel.move(1)

        application.simulator.simulate()

    def open_map_menu(context: CommandContext) -> None:
        context.app.push_menu(
            build_map_menu(application)
        )

    def display_map_note(context: CommandContext) -> None:
        if application.map_config is not None:
            context.menu.screen_context.message = application.map_config.note
        context.menu.set_command_label(map_note_command, "Hide map note")
        context.menu.set_command_behavior(map_note_command, hide_map_note)

    def hide_map_note(context: CommandContext) -> None:
        if application.map_config is not None:
            context.menu.screen_context.message = None
        context.menu.set_command_label(map_note_command, "Show map note")
        context.menu.set_command_behavior(map_note_command, display_map_note)

    menu.add_command(
        label="Run simulation",
        behavior=run_simulation
    )

    menu.add_command(
        label="Change map",
        behavior=open_map_menu
    )

    map_note_command = menu.add_command(
        label="Show map note",
        behavior=display_map_note
    )

    return menu
