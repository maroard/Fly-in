from __future__ import annotations
from typing import TYPE_CHECKING

from tuiloom import CommandContext, ScreenContext, TerminalMenu

if TYPE_CHECKING:
    from src.application import Application
from src.ui.menus.map_menu import build_map_menu


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
        if application.renderer is not None:
            context.menu.set_content_source(application.renderer.render)

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
