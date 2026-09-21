from tuiloom import ContentSize

from src.domain.graph import Graph
from src.rendering.canvas import Canvas
from src.rendering.line_drawing import get_line_points
from src.rendering.projection import Projector


class Renderer:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.padding: int = 2

    def render(self, size: ContentSize) -> list[str]:
        canvas = Canvas(size.width, size.height)
        projector = Projector(
            min_x=min(zone.x for zone in self.graph.zones.values()),
            max_x=max(zone.x for zone in self.graph.zones.values()),
            min_y=min(zone.y for zone in self.graph.zones.values()),
            max_y=max(zone.y for zone in self.graph.zones.values()),
            width=size.width - 2 * self.padding,
            height=size.height - 2 * self.padding,
        )

        self._draw_connections(canvas, projector)
        self._draw_zones(canvas, projector)

        return canvas.to_lines()

    def _draw_connections(self, canvas: Canvas, projector: Projector) -> None:
        for connection in self.graph.connections:
            zone1 = self.graph.zones[connection.zone_name1]
            zone2 = self.graph.zones[connection.zone_name2]

            zone1_position = self._project(projector, zone1.x, zone1.y)
            zone2_position = self._project(projector, zone2.x, zone2.y)

            for x, y in get_line_points(
                start=zone1_position,
                end=zone2_position,
            ):
                canvas.set(x, y, "·")

    def _draw_zones(self, canvas: Canvas, projector: Projector) -> None:
        for zone in self.graph.zones.values():
            x, y = self._project(projector, zone.x, zone.y)
            canvas.set(x, y, "●")

    def _project(
        self,
        projector: Projector,
        x: int,
        y: int
    ) -> tuple[int, int]:
        screen_x, screen_y = projector.project(x, y)
        return (
            screen_x + self.padding,
            screen_y + self.padding,
        )
