from __future__ import annotations

from typing import TYPE_CHECKING

from tuiloom import CommandContext, ScreenContent, ScreenContext, TerminalMenu

from src.output.formatter import format_turn
from src.simulation.simulator import Simulator
from src.ui.menus.settings_menu import build_settings_menu

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
        if application.renderer is None:
            return

        if application.simulator is None:
            try:
                application.simulator = Simulator(
                    application.renderer.graph,
                    occupancy=application.renderer.occupancy,
                )
            except RuntimeError as error:
                context.menu.show_alert(str(error))
                return

        application.graph_panel = context.menu.set_content(
            ScreenContent.responsive(
                application.renderer.render,
                min_width=40,
                min_height=20,
                refresh_mode="resize",
            ),
            description="Graph",
        )
        application.graph_panel.move(0)

        def render_turns() -> list[str]:
            if application.simulator is None:
                return []
            return [
                f"Tour {turn.number}: {format_turn(turn.movements)}"
                for turn in application.simulator.state.turns
            ]

        turns_content = ScreenContent.dynamic(render_turns)
        if application.output_panel is None:
            application.output_panel = context.menu.add_content_panel(
                turns_content,
                description="Simulation",
                position=1,
            )
        else:
            application.output_panel.set_content(turns_content)
            application.output_panel.move(1)

        application.simulator.simulate()

    def credit(context: CommandContext) -> None:
        context.menu.toggle_message("credit")

    menu.add_command(label="Run simulation", behavior=run_simulation)
    menu.add_menu(submenu=build_settings_menu(application), label="Settings")
    menu.add_command(label="Credit", behavior=credit)
    return menu
