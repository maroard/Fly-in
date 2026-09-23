from __future__ import annotations
from typing import TYPE_CHECKING

from tuiloom import CommandContext, ScreenContent, ScreenContext, TerminalMenu

from src.simulation.simulator import Simulator

if TYPE_CHECKING:
    from src.application import Application


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

    def run_simulation(context: CommandContext) -> None:
        if application.renderer is not None:
            if application.simulator is None:
                try:
                    application.simulator = Simulator(
                        application.renderer.graph,
                        occupancy=application.renderer.occupancy,
                    )
                except RuntimeError as error:
                    context.menu.show_alert(str(error))
                    return
            application.content_panel = context.menu.set_content(
                ScreenContent.responsive(
                    application.renderer.render,
                    min_width=40,
                    min_height=20,
                    refresh_mode="resize",
                )
            )

    def credit(context: CommandContext) -> None:
        context.menu.toggle_message("credit")

    menu.add_command(
        label="Run simulation",
        behavior=run_simulation
    )

    menu.add_command(
        label="Credit",
        behavior=credit
    )

    return menu
