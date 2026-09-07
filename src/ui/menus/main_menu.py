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

    def open_map_menu(context: CommandContext) -> None:
        context.app.push_menu(
            build_map_menu(application)
        )

    menu.add_command(
        label="Change map",
        behavior=open_map_menu,
    )

    def display_map_note(context: CommandContext) -> None:
        context.menu.screen_context.message = application.map_config.note

    menu.add_command(
        label="Show map note",
        behavior=display_map_note
    )

    return menu
