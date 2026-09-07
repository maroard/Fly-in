from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tuiloom import CommandContext, ScreenContext, TerminalMenu

from src.parsing.parser import Parser

if TYPE_CHECKING:
    from src.application import Application


def build_map_menu(application: Application) -> TerminalMenu:
    app = application.terminal_app
    menu = TerminalMenu(
        app,
        ScreenContext(
            menu_name="maps",
            title="Map Categories",
            text="Please select a map category:",
            width=40
        )
    )

    map_folders = sorted(
        path for path in Path("maps").iterdir() if path.is_dir()
    )
    for folder in map_folders:
        category_menu = TerminalMenu(
            app,
            ScreenContext(
                menu_name=f"Category:{folder.name}",
                title=folder.name.capitalize(),
                text="Please select a map:",
                width=40
            )
        )

        map_screen(category_menu, folder, application)
        menu.add_menu(category_menu, folder.name.capitalize())

    return menu


def map_screen(
    menu: TerminalMenu,
    category_path: Path,
    application: Application,
) -> None:
    maps = sorted(
        path for path in category_path.iterdir() if path.is_file()
    )
    for map_path in maps:
        def select(
            context: CommandContext,
            selected_map: Path = map_path
        ) -> None:
            application.map_path = selected_map
            application.parser = Parser(selected_map)
            application.map_config = application.parser.process()

            application.main_menu.screen_context.text = (
                f"Current map: {category_path.name}/{selected_map.name}"
            )
            context.app.reset_to(application.main_menu)

        menu.add_command(label=map_path.name, behavior=select)
