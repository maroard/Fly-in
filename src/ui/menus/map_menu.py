"""List map categories and load selected map resources."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from tuiloom import (
    ChoiceContext,
    ChoiceOption,
    MenuDisplay,
    TerminalMenu,
)

from src.domain.graph import Graph
from src.parsing.parser import Parser
from src.rendering.renderer import Renderer

if TYPE_CHECKING:
    from src.application import Application


class MapMenu:
    """Build map choices and load the selected map into the application.

    Attributes:
        application: Shared state receiving the selected map resources.
        menu: Terminal menu containing category map choices.
    """

    @classmethod
    def build(cls, application: Application) -> TerminalMenu:
        """Create a Tuiloom menu backed by a MapMenu instance.

        Args:
            application: Shared application state used by the menu or test
                helper.

        Returns:
            Map selection menu with callbacks bound to its owner.
        """
        return cls(application).menu

    def __init__(self, application: Application) -> None:
        """Create the menu and populate its map categories.

        Args:
            application: Shared application state used by the menu or test
                helper.
        """
        self.application = application

        self.menu = TerminalMenu(
            application.terminal_app,
            MenuDisplay(
                menu_name="maps",
                title="Map Menu",
                text="Please select a category and map:",
                width=40,
            ),
            presentation="overlay",
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
                len(category_order)
            ),
        )

        for folder in map_folders:
            self.add_map_category_choice(folder)

    def add_map_category_choice(self, category_path: Path) -> None:
        """Add a category with a callback bound to its map files.

        Args:
            category_path: Directory containing the map files for one menu
                category.
        """
        maps = sorted(
            path
            for path in category_path.iterdir()
            if path.is_file()
        )

        if not maps:
            return

        self.menu.add_choice(
            label=category_path.name.capitalize(),
            options=[ChoiceOption(path.name) for path in maps],
            on_select=partial(self.select_map, maps=maps),
            vertical=True,
            selected_index=(
                maps.index(self.application.map_path)
                if self.application.map_path in maps
                else None
            ),
        )

    def select_map(self, context: ChoiceContext, maps: list[Path]) -> None:
        """Choose and activate a map within a category choice.

        Args:
            context: Tuiloom callback context containing the selected
                option index.
            maps: Map paths ordered like the category choice options.
        """
        application = self.application

        application.map_path = maps[context.index]
        application.parser = Parser(application.map_path)
        application.map_config = application.parser.process()

        application.graph = Graph(application.map_config)
        application.renderer = Renderer(application.graph)

        application.simulator = None
        application.playback = None

        if application.playback_tick is not None:
            application.playback_tick.cancel()
            application.playback_tick = None

        for panel in (
            application.graph_panel,
            application.simulation_panel,
            application.stats_panel,
            application.movement_panel,
        ):
            if panel is not None:
                panel.remove()

        application.graph_panel = None
        application.simulation_panel = None
        application.stats_panel = None
        application.movement_panel = None

        application.main_menu.refresh_status_bar()
        context.app.reset_to(application.main_menu)
