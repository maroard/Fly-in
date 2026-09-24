from pathlib import Path
from typing import Literal

from tuiloom import ContentPanel, TerminalApp, TerminalMenu, style

from src.ui.menus.main_menu import build_main_menu
from src.ui.menus.map_menu import build_map_menu
from src.parsing.parser import Parser
from src.parsing.map_config import MapConfig
from src.domain.graph import Graph
from src.rendering.renderer import Renderer
from src.simulation.simulator import Simulator


type SimulationMode = Literal["one_shot", "step_by_step"]
type SimulationSpeed = Literal["low", "medium", "high", "flash"]


class Application:
    def __init__(self) -> None:
        self.map_path: Path | None = None
        self.parser: Parser | None = None
        self.map_config: MapConfig | None = None

        self.graph: Graph | None = None
        self.renderer: Renderer | None = None
        self.simulator: Simulator | None = None

        self.graph_panel: ContentPanel | None = None
        self.output_panel: ContentPanel | None = None
        self.simulation_mode: SimulationMode = "one_shot"
        self.simulation_speed: SimulationSpeed | None = "medium"

        self._build_ui()

    def _build_ui(self) -> None:
        self.terminal_app: TerminalApp = TerminalApp(
            style(
                "Fly-in",
                bold=True,
                underline=True,
            )
        )

        self._set_messages()
        self.main_menu: TerminalMenu = build_main_menu(self)
        self.terminal_app.set_main_menu(self.main_menu)

    def _set_messages(self) -> None:
        self.terminal_app.add_message(
            key="credit",
            text=style(
                "This project has been created as part "
                "of the 42 curriculum by maroard.",
                italic=True,
            ),
        )

        self.terminal_app.add_message(
            key="one_shot",
            text=(
                f"{style("One shot", bold=True)}: "
                "Run the simulation until all drones arrive."
            )
        )

        self.terminal_app.add_message(
            key="step_by_step",
            text=(
                f"{style("Step by step", bold=True)}: "
                "Advance the simulation one turn at a time."
            )
        )

    def run(self) -> None:
        self.terminal_app.run(
            entry_menu=build_map_menu(self)
        )
