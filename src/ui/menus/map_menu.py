from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING


from tuiloom import ChoiceContext, ChoiceOption, MenuDisplay, TerminalMenu

from src.parsing.parser import Parser
from src.domain.graph import Graph
from src.rendering.renderer import Renderer

if TYPE_CHECKING:
    from src.application import Application


def build_map_menu(application: Application) -> TerminalMenu:
    app = application.terminal_app
    menu = TerminalMenu(
        app,
        MenuDisplay(
            menu_name="maps",
            title="Map Menu",
            text="Please select a category and map:",
            width=40
        ),
        presentation="overlay"
    )

    category_order = {
        "easy": 0,
        "medium": 1,
        "hard": 2,
        "challenger": 3,
    }

    map_folders = sorted(
        (
            path
            for path in Path("maps").iterdir()
            if path.is_dir()
        ),
        key=lambda path: category_order.get(
            path.name.lower(),
            len(category_order),
        )
    )

    for folder in map_folders:
        add_map_category_choice(menu, folder, application)

    return menu


def add_map_category_choice(
    menu: TerminalMenu,
    category_path: Path,
    application: Application,
) -> None:
    maps = sorted(
        path for path in category_path.iterdir() if path.is_file()
    )

    if not maps:
        return

    def select(context: ChoiceContext) -> None:
        selected_map = maps[context.index]
        application.map_path = selected_map
        application.parser = Parser(selected_map)
        application.map_config = application.parser.process()
        application.graph = Graph(application.map_config)
        application.renderer = Renderer(application.graph)
        application.simulator = None
        application.playback = None
        if application.playback_tick is not None:
            application.playback_tick.cancel()
            application.playback_tick = None

        if application.graph_panel is not None:
            application.graph_panel.remove()
        if application.simulation_panel is not None:
            application.simulation_panel.remove()
        if application.stats_panel is not None:
            application.stats_panel.remove()
        if application.movement_panel is not None:
            application.movement_panel.remove()
        application.graph_panel = None
        application.simulation_panel = None
        application.stats_panel = None
        application.movement_panel = None

        application.main_menu.refresh_status_bar()
        context.app.reset_to(application.main_menu)

    menu.add_choice(
        label=category_path.name.capitalize(),
        options=[ChoiceOption(map_path.name) for map_path in maps],
        on_select=select,
        vertical=True,
        selected_index=(
            maps.index(application.map_path)
            if application.map_path in maps
            else None
        ),
    )
