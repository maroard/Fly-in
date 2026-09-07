from pathlib import Path

import pytest
from tuiloom import CommandContext, TerminalMenu

from src.application import Application


def activate(menu: TerminalMenu, label: str) -> None:
    command = next(
        command for command in menu.commands if command.label == label
    )
    command.behavior(CommandContext(menu.app, menu, command, None))


def test_initial_map_selection_and_later_map_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application = Application()
    entry_menus: list[TerminalMenu] = []
    monkeypatch.setattr(
        application.terminal_app,
        "run",
        lambda entry_menu=None: entry_menus.append(entry_menu),
    )

    application.run()

    assert len(entry_menus) == 1
    map_menu = entry_menus[0]
    assert application.main_menu is not map_menu
    assert [command.label for command in application.main_menu.commands] == [
        "Change map"
    ]
    main_text = application.main_menu.screen_context.text
    assert main_text is not None
    assert "No map selected" in main_text

    application.terminal_app.push_menu(map_menu)
    activate(map_menu, "Easy")
    easy_menu = application.terminal_app._menu_stack[-1]
    assert application.terminal_app._menu_stack == [
        map_menu, easy_menu
    ]

    activate(easy_menu, "01_linear_path.txt")
    assert application.map == Path("maps/easy/01_linear_path.txt")
    main_text = application.main_menu.screen_context.text
    assert main_text is not None
    assert "easy/01_linear_path.txt" in main_text
    assert application.terminal_app._menu_stack == [application.main_menu]

    activate(application.main_menu, "Change map")
    map_menu = application.terminal_app._menu_stack[-1]
    activate(map_menu, "Medium")
    medium_menu = application.terminal_app._menu_stack[-1]
    assert application.terminal_app._menu_stack == [
        application.main_menu,
        map_menu,
        medium_menu,
    ]

    activate(medium_menu, "01_dead_end_trap.txt")
    assert application.map == Path("maps/medium/01_dead_end_trap.txt")
    main_text = application.main_menu.screen_context.text
    assert main_text is not None
    assert "medium/01_dead_end_trap.txt" in main_text
    assert application.terminal_app._menu_stack == [application.main_menu]
