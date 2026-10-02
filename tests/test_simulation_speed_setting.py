import pytest
from tuiloom import CommandContext, MenuChoice
from tuiloom.render.menu_renderer import MenuRenderer

from src.application import Application
from src.ui.menus.settings_menu import SettingsMenu


def select_speed(application: Application, index: int) -> None:
    menu = SettingsMenu.build(application)
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


@pytest.mark.parametrize("text", ["0.01", "31", "abc", "nan", "inf"])
def test_custom_duration_rejects_invalid_value_and_allows_retry(
    text: str,
) -> None:
    application = Application()
    menu = SettingsMenu.build(application)
    choice = next(
        command for command in menu.commands
        if command.label == "Simulation speed"
    )
    assert isinstance(choice, MenuChoice)
    menu.set_choice_index(choice, 3)
    choice.callback(CommandContext(menu.app, menu, choice, None))
    assert menu._input is not None
    menu._input.callback(text)
    assert menu.display_state.message == SettingsMenu.INVALID_SPEED_MESSAGE
    assert SettingsMenu.INVALID_SPEED_MESSAGE in MenuRenderer(menu).render()
    assert application.custom_seconds == 1.0
    assert menu._input is not None
    menu._input.callback("1.5")
    assert application.custom_seconds == 1.5
    assert menu.display_state.message is None
    assert menu._input is None
