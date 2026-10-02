"""Coordinate map resources, simulation settings and terminal menus."""

from pathlib import Path
from typing import Literal

from tuiloom import (
    ContentPanel,
    TerminalApp,
    TerminalMenu,
    TickHandle,
    style,
)

from src.ui.menus.main_menu import MainMenu
from src.ui.menus.map_menu import MapMenu
from src.parsing.parser import Parser
from src.parsing.map_config import MapConfig
from src.domain.graph import Graph
from src.rendering.renderer import Renderer
from src.simulation.simulator import Simulator
from src.simulation.playback import Playback
from src.pathfinding.routing_mode import RoutingMode


SimulationMode = Literal["one_shot", "step_by_step"]
SimulationSpeed = Literal["low", "medium", "high", "custom"]


class Application:
    """Share map data, simulation settings and terminal UI state.

    Attributes:
        map_path: Selected map file, or None before map selection.
        graph: Loaded graph, or None before map selection.
        renderer: Renderer for the loaded graph.
        simulator: Most recently installed simulator.
        playback: Visible playback of the calculated simulation.
        terminal_app: Terminal event loop and menu stack.
        main_menu: Main terminal menu containing simulation panels.
    """

    def __init__(self) -> None:
        """Initialize application state and build the menus."""
        self.map_path: Path | None = None
        self.parser: Parser | None = None
        self.map_config: MapConfig | None = None

        self.graph: Graph | None = None
        self.renderer: Renderer | None = None
        self.simulator: Simulator | None = None

        self.graph_panel: ContentPanel | None = None
        self.simulation_panel: ContentPanel | None = None
        self.movement_panel: ContentPanel | None = None
        self.stats_panel: ContentPanel | None = None

        self.playback: Playback | None = None
        self.playback_tick: TickHandle | None = None

        self.simulation_mode: SimulationMode = "one_shot"
        self.simulation_speed: SimulationSpeed = "medium"
        self.custom_seconds = 1.0
        self.drones_routing_mode: RoutingMode = "single-path"

        self._build_ui()

    @property
    def seconds_per_movement(self) -> float:
        """Return the animation duration selected by the speed setting.

        Returns:
            Movement duration in seconds for the selected preset or custom
            value.
        """
        return {
            "low": 2.0,
            "medium": 1.0,
            "high": 0.4,
            "custom": self.custom_seconds,
        }[self.simulation_speed]

    def _build_ui(self) -> None:
        """Create the terminal application and install its main menu."""
        self.terminal_app: TerminalApp = TerminalApp(
            style(
                "Fly-in",
                bold=True,
                underline=True,
            )
        )

        self._set_messages()

        self.main_menu: TerminalMenu = MainMenu.build(self)
        self.terminal_app.set_main_menu(self.main_menu)

    def _set_messages(self) -> None:
        """Register credits and descriptions for simulation settings."""
        for key, text in {
            "credit": f"{
                style(
                    "This project has been created as part "
                    "of the 42 curriculum by maroard.",
                    italic=True,
                )
            }",
            "one_shot": "Run the simulation until all drones arrive.",
            "step_by_step": "Advance the simulation one movement at a time.",
            "speed_low": "2 seconds per movement.",
            "speed_medium": "1 second per movement.",
            "speed_high": "0.4 seconds per movement.",
            "speed_custom": (
                "Choose a duration from 0.1 to 30 seconds "
                "per movement."
            ),
            "routing_single_path": "Use the same path for all drones.",
            "routing_multi_path": (
                "Try alternative paths when a drone is blocked."
            ),
        }.items():
            self.terminal_app.add_message(
                key=key,
                text=text
            )

    def run(self) -> None:
        """Start the terminal event loop with the map selection menu."""
        self.terminal_app.run(
            entry_menu=MapMenu.build(self)
        )
