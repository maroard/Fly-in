"""Configure playback mode, animation speed and drone routing."""

from __future__ import annotations

from math import isfinite
from typing import TYPE_CHECKING

from tuiloom import (
    ChoiceContext,
    ChoiceOption,
    CommandContext,
    MenuDisplay,
    TerminalMenu,
)

from src.ui.menus.map_menu import MapMenu

if TYPE_CHECKING:
    from src.application import Application, SimulationSpeed


class SettingsMenu:
    """Own simulation settings and custom speed input callbacks.

    Attributes:
        application: Shared simulation and routing settings.
        menu: Terminal menu containing settings and custom speed input.
    """

    INVALID_SPEED_MESSAGE = "Enter a duration from 0.1 to 30 seconds."

    @classmethod
    def build(cls, application: Application) -> TerminalMenu:
        """Create a Tuiloom menu backed by a SettingsMenu instance.

        Args:
            application: Shared application state used by the menu or test
                helper.

        Returns:
            Settings menu with callbacks bound to its owner.
        """
        return cls(application).menu

    def __init__(self, application: Application) -> None:
        """Create the menu with the application's current settings.

        Args:
            application: Shared application state used by the menu or test
                helper.
        """
        self.application = application

        self.menu = TerminalMenu(
            application.terminal_app,
            MenuDisplay(
                menu_name="settings",
                title="Settings",
                width=40,
            ),
            presentation="overlay",
        )

        self.menu.add_command(
            label="Change map",
            callback=self.open_map_menu,
        )

        self.menu.add_choice(
            "Simulation mode",
            [
                ChoiceOption(
                    "One shot",
                    hover_message="one_shot"
                ),
                ChoiceOption(
                    "Step by step",
                    hover_message="step_by_step"
                ),
            ],
            on_select=self.select_simulation_mode,
            selected_index=(
                0 if application.simulation_mode == "one_shot" else 1
            ),
        )

        self.menu.add_choice(
            "Simulation speed",
            [
                ChoiceOption(
                    label,
                    hover_message=f"speed_{label.lower()}"
                )
                for label in ("Low", "Medium", "High", "Custom")
            ],
            on_select=self.select_simulation_speed,
            selected_index=("low", "medium", "high", "custom").index(
                application.simulation_speed
            ),
        )

        self.menu.add_choice(
            "Drones routing mode",
            [
                ChoiceOption(
                    "Single-path",
                    hover_message="routing_single_path"
                ),
                ChoiceOption(
                    "Multi-path",
                    hover_message="routing_multi_path"
                ),
            ],
            on_select=self.select_drones_routing_mode,
            selected_index=(
                0 if application.drones_routing_mode == "single-path" else 1
            ),
        )

    def open_map_menu(self, context: CommandContext) -> None:
        """Open a fresh map menu reflecting the currently selected map.

        Args:
            context: Tuiloom command context containing the application and
                menu.
        """
        context.app.push_menu(MapMenu.build(self.application))

    def select_simulation_mode(self, context: ChoiceContext) -> None:
        """Set automatic or step-by-step playback.

        Args:
            context: Tuiloom callback context containing the selected
                option index.
        """
        self.application.simulation_mode = (
            "one_shot" if context.index == 0 else "step_by_step"
        )

    def select_drones_routing_mode(self, context: ChoiceContext) -> None:
        """Set single-path or multi-path routing.

        Args:
            context: Tuiloom callback context containing the selected
                option index.
        """
        self.application.drones_routing_mode = (
            "single-path" if context.index == 0 else "multi-path"
        )

    def select_simulation_speed(self, context: ChoiceContext) -> None:
        """Select a speed preset or open the custom duration input.

        Args:
            context: Tuiloom callback context containing the selected
                option index.
        """
        if self.menu.display_state.message == self.INVALID_SPEED_MESSAGE:
            self.menu.clear_message()

        speeds: tuple[SimulationSpeed, ...] = (
            "low",
            "medium",
            "high",
            "custom"
        )

        self.application.simulation_speed = speeds[context.index]

        if self.application.simulation_speed == "custom":
            self.menu.enter_input_mode(
                "Seconds per movement: ",
                self.save_custom_speed
            )

    def save_custom_speed(self, text: str) -> None:
        """Validate and save a movement duration between 0.1 and 30 seconds.

        Args:
            text: User input containing the movement duration in seconds.
        """
        try:
            seconds = float(text)
        except ValueError:
            seconds = 0.0

        if not isfinite(seconds) or not 0.1 <= seconds <= 30:
            self.menu.display_state.message = self.INVALID_SPEED_MESSAGE
            return

        self.application.custom_seconds = seconds

        if self.menu.display_state.message == self.INVALID_SPEED_MESSAGE:
            self.menu.clear_message()

        self.menu.leave_input_mode()
