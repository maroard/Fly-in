from __future__ import annotations
from typing import TYPE_CHECKING

from tuiloom import (
    ChoiceContext,
    ChoiceOption,
    CommandContext,
    ScreenContext,
    TerminalMenu,
)

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

    def select_simulation_mode(context: ChoiceContext) -> None:
        if context.index == 0:
            application.simulation_mode = "one_shot"
        else:
            application.simulation_mode = "step_by_step"

    # def select_simulation_speed(context: ChoiceContext) -> None:


    menu.add_command(
        label="Change map",
        behavior=open_map_menu
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

    # menu.add_choice(
    #     "Simulation speed",
    #     [
    #         ChoiceOption("Low"),
    #         ChoiceOption("Medium"),
    #         ChoiceOption("High"),
    #         ChoiceOption("Flash")
    #     ],
    #     on_select=select_simulation_speed,
    #     selected_index=,
    # )

    return menu
