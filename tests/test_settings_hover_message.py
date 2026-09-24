from tuiloom import KeyBinding
from tuiloom.input_handler.input_event import InputEvent
from tuiloom.render.menu_renderer import MenuRenderer

from src.application import Application
from src.ui.menus.settings_menu import build_settings_menu


def test_mode_descriptions_follow_hover_without_replacing_footer() -> None:
    application = Application()
    menu = build_settings_menu(application)
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
    assert "Advance the simulation one turn at a time" in renderer.render()
    press("down")
    assert "42 curriculum" in renderer.render()
    assert "Advance the simulation one turn at a time" not in renderer.render()
