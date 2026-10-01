"""Enable modified character keys during Tuiloom's interactive session."""

from sys import stdout

from tuiloom import TerminalApp


class KeyboardTerminalApp(TerminalApp):
    def _run_application_loop(self) -> None:
        # Tuiloom 0.12.1 decodes CSI-u but does not request it. Push the
        # disambiguation flag after entering the alternate screen, whose
        # keyboard protocol stack is independent of the normal screen.
        stdout.write("\x1b[>1u")
        stdout.flush()
        try:
            super()._run_application_loop()
        finally:
            stdout.write("\x1b[<u")
            stdout.flush()
