from src.domain.graph import Graph
from src.rendering.projection import Projector
from src.rendering.canvas import Canvas

from src.rendering.line_drawing import get_line_points


class Renderer:
    def __init__(self, graph: Graph, width: int, height: int) -> None:
        self.graph = graph
        self.width = width
        self.height = height

        min_x = min(zone.x for zone in self.graph.zones.values())
        max_x = max(zone.x for zone in self.graph.zones.values())
        min_y = min(zone.y for zone in self.graph.zones.values())
        max_y = max(zone.y for zone in self.graph.zones.values())
        self.padding: int = 2

        self.projector = Projector(
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            width=width - 2 * self.padding,
            height=height - 2 * self.padding
        )

    def render(self) -> list[str]:
        canvas = Canvas(self.width, self.height)

        self._draw_connections(canvas)
        self._draw_zones(canvas)

        return canvas.to_lines()

    def _draw_connections(self, canvas: Canvas) -> None:
        for connection in self.graph.connections:
            zone1 = self.graph.zones[connection.zone_name1]
            zone2 = self.graph.zones[connection.zone_name2]

            zone1_position = self._project(zone1.x, zone1.y)
            zone2_position = self._project(zone2.x, zone2.y)

            for x, y in get_line_points(
                start=zone1_position,
                end=zone2_position,
            ):
                canvas.set(x, y, "·")

    def _draw_zones(self, canvas: Canvas) -> None:
        for zone in self.graph.zones.values():
            x, y = self._project(zone.x, zone.y)

            canvas.set(x, y, '●')

    def _project(self, x: int, y: int) -> tuple[int, int]:
        screen_x, screen_y = self.projector.project(x, y)

        return (
            screen_x + self.padding,
            screen_y + self.padding,
        )
