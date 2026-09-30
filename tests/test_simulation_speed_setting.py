from tuiloom import CommandContext, MenuChoice

from src.application import Application
from src.ui.menus.settings_menu import build_settings_menu


def select_speed(application: Application, index: int) -> None:
    menu = build_settings_menu(application)
    choice = next(
        command for command in menu.commands
        if command.label == "Simulation speed"
    )
    assert isinstance(choice, MenuChoice)
    menu.set_choice_index(choice, index)
    choice.callback(CommandContext(menu.app, menu, choice, None))
    if index == 3:
        assert menu._input is not None
        menu._input.callback("1.5")


def test_speed_presets_and_custom_duration() -> None:
    application = Application()
    for index, expected in enumerate((2.0, 1.0, 0.4)):
        select_speed(application, index)
        assert application.seconds_per_movement == expected
    select_speed(application, 3)
    assert application.seconds_per_movement == 1.5


def test_custom_duration_rejects_out_of_range_value() -> None:
    application = Application()
    menu = build_settings_menu(application)
    choice = next(
        command for command in menu.commands
        if command.label == "Simulation speed"
    )
    assert isinstance(choice, MenuChoice)
    menu.set_choice_index(choice, 3)
    choice.callback(CommandContext(menu.app, menu, choice, None))
    assert menu._input is not None
    menu._input.callback("0.01")
    assert menu._alert is not None
    assert application.custom_seconds == 1.0
