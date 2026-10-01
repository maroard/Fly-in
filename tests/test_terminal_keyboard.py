from io import StringIO

import pytest
from tuiloom import TerminalApp

from src.ui.terminal_app import KeyboardTerminalApp


@pytest.mark.parametrize("fail", [False, True])
def test_keyboard_protocol_is_scoped_to_application_loop(
    monkeypatch: pytest.MonkeyPatch, fail: bool,
) -> None:
    output = StringIO()
    monkeypatch.setattr("src.ui.terminal_app.stdout", output)

    def loop(app: TerminalApp) -> None:
        assert output.getvalue() == "\x1b[>1u"
        if fail:
            raise RuntimeError("loop failure")

    monkeypatch.setattr(TerminalApp, "_run_application_loop", loop)
    app = KeyboardTerminalApp("Test")
    if fail:
        with pytest.raises(RuntimeError, match="loop failure"):
            app._run_application_loop()
    else:
        app._run_application_loop()
    assert output.getvalue() == "\x1b[>1u\x1b[<u"
