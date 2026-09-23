from __future__ import annotations
from typing import TYPE_CHECKING

from tuiloom import CommandContext, ScreenContext, TerminalMenu

if TYPE_CHECKING:
    from src.application import Application
from src.ui.menus.map_menu import build_map_menu


def build_settings_menu(application: Application) -> TerminalMenu:
    menu = TerminalMenu(
        application.terminal_app,
        ScreenContext(
            menu_name="settings",
            title="Settings",
            width=40,
        )
    )

    def open_map_menu(context: CommandContext) -> None:
        context.app.push_menu(
            build_map_menu(application)
        )

    menu.add_command(
        label="Change map",
        behavior=open_map_menu
    )

    return menu
