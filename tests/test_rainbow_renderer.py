import pytest

from tuiloom import AnimationFrame, CommandContext, ContentSize, style

from src.application import Application
from src.domain.connection import Connection, ConnectionMetadata
from src.domain.graph import Graph
from src.domain.zone import Zone, ZoneMetadata
from src.parsing.map_config import MapConfig
from src.rendering.renderer import Renderer


def rainbow_graph(end_color: str = "rainbow") -> Graph:
    start = Zone(name="start", x=0, y=0)
    fixed = Zone(
        name="fixed",
        x=1,
        y=0,
        metadata=ZoneMetadata(color="blue", zone_type="priority"),
    )
    end = Zone(name="end", x=2, y=0, metadata=ZoneMetadata(color=end_color))
    return Graph(
        MapConfig(
            1,
            start,
            end,
            {zone.name: zone for zone in (start, fixed, end)},
            [
                Connection("start", "fixed", ConnectionMetadata()),
                Connection("fixed", "end", ConnectionMetadata()),
            ],
        )
    )


def test_rainbow_hub_changes_color_while_fixed_hub_stays_blue() -> None:
    renderer = Renderer(rainbow_graph())
    size = ContentSize(40, 20)
    first = "\n".join(renderer.render(size, AnimationFrame(0.0, 0)))
    second = "\n".join(renderer.render(size, AnimationFrame(0.3, 4)))

    assert style("●", foreground=(255, 0, 0), bold=True) in first
    assert style("●", foreground=(255, 127, 0), bold=True) in second
    assert style("●", foreground="blue", bold=True) in first
    assert style("●", foreground="blue", bold=True) in second
    assert renderer.render(size) == renderer.render(
        size, AnimationFrame(0.0, 0)
    )


@pytest.mark.parametrize("end_color", ["rainbow", "green"])
def test_every_simulation_uses_animated_graph_panel(end_color: str) -> None:
    application = Application()
    application.renderer = Renderer(rainbow_graph(end_color))
    menu = application.main_menu
    command = next(
        command
        for command in menu.commands
        if command.label == "Run simulation"
    )
    command.callback(
        CommandContext(application.terminal_app, menu, command, None)
    )

    assert application.graph_panel is not None
    assert application.graph_panel._content._kind == "animated"
    assert application.graph_panel._content.fps == 20
