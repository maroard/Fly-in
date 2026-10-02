from tuiloom import KeyBinding
from tuiloom.input_handler.input_event import InputEvent
from tuiloom.render.menu_renderer import MenuRenderer

from src.application import Application
from src.ui.menus.settings_menu import SettingsMenu


def test_mode_descriptions_follow_hover_without_replacing_footer() -> None:
    application = Application()
    menu = SettingsMenu.build(application)
    menu.show_message("credit")
    menu._prepare_open()
    renderer = MenuRenderer(menu)

    def press(key: str) -> None:
        menu._handle_event(InputEvent(KeyBinding(key), None))

    press("down")
    press("right")
    assert "Run the simulation until all drones arrive" in renderer.render()
    assert menu.active_message_key == "credit"
    press("right")
    step_help = "Advance the simulation one movement at a time"
    assert step_help in renderer.render()
    press("down")
    assert "42 curriculum" in renderer.render()
    assert step_help not in renderer.render()

    for speed_help in (
        "2 seconds per movement.",
        "1 second per movement.",
        "0.4 seconds per movement.",
        "Choose a duration from 0.1 to 30 seconds per movement.",
    ):
        press("right")
        assert speed_help in renderer.render()
        assert menu.active_message_key == "credit"
    assert application.simulation_speed == "medium"
    press("down")
    for routing_help in (
        "Use the same path for all drones.",
        "Try alternative paths when a drone is blocked.",
    ):
        press("right")
        assert routing_help in renderer.render()
        assert menu.active_message_key == "credit"
    assert application.drones_routing_mode == "single-path"
