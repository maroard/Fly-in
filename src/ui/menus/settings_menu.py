from __future__ import annotations
from typing import TYPE_CHECKING
from math import isfinite

from tuiloom import (
    ChoiceContext,
    ChoiceOption,
    CommandContext,
    MenuDisplay,
    TerminalMenu,
)

if TYPE_CHECKING:
    from src.application import Application, SimulationSpeed
from src.ui.menus.map_menu import build_map_menu


def build_settings_menu(application: Application) -> TerminalMenu:
    menu = TerminalMenu(
        application.terminal_app,
        MenuDisplay(
            menu_name="settings",
            title="Settings",
            width=40,
        ),
        presentation="overlay"
    )

    def open_map_menu(context: CommandContext) -> None:
        context.app.push_menu(
            build_map_menu(application)
        )

    def select_simulation_mode(context: ChoiceContext) -> None:
        if context.index == 0:
            application.simulation_mode = "one_shot"
        else:
            application.simulation_mode = "step_by_step"

    def select_drones_routing_mode(context: ChoiceContext) -> None:
        if context.index == 0:
            application.drones_routing_mode = "single-path"
        else:
            application.drones_routing_mode = "multi-path"

    def select_simulation_speed(context: ChoiceContext) -> None:
        speeds: tuple[SimulationSpeed, ...] = (
            "low", "medium", "high", "custom"
        )
        application.simulation_speed = speeds[context.index]
        if application.simulation_speed != "custom":
            return

        def save_custom_speed(text: str) -> None:
            try:
                seconds = float(text)
            except ValueError:
                seconds = 0.0
            if not isfinite(seconds) or not 0.1 <= seconds <= 30:
                context.menu.show_alert(
                    "Enter a duration from 0.1 to 30 seconds."
                )
                return
            application.custom_seconds = seconds
            context.menu.leave_input_mode()

        context.menu.enter_input_mode(
            "Seconds per movement: ", save_custom_speed
        )

    menu.add_command(
        label="Change map",
        callback=open_map_menu
    )

    menu.add_choice(
        "Simulation mode",
        [
            ChoiceOption("One shot", hover_message="one_shot"),
            ChoiceOption("Step by step", hover_message="step_by_step")
        ],
        on_select=select_simulation_mode,
        selected_index=0 if application.simulation_mode == "one_shot" else 1,
    )

    menu.add_choice(
        "Simulation speed",
        [ChoiceOption(label) for label in ("Low", "Medium", "High", "Custom")],
        on_select=select_simulation_speed,
        selected_index=("low", "medium", "high", "custom").index(
            application.simulation_speed
        ),
    )

    menu.add_choice(
        "Drones routing mode",
        [
            ChoiceOption("Single-path"),
            ChoiceOption("Multi-path")
        ],
        on_select=select_drones_routing_mode,
        selected_index=0
        if application.drones_routing_mode == "single-path" else 1,
    )

    return menu
