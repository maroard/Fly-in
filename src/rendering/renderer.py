from tuiloom import (
    AnimationFrame,
    ContentSize,
    TextColor,
    rainbow_color,
    style,
)

from src.domain.graph import Graph
from src.rendering.canvas import Canvas
from src.rendering.line_drawing import get_line_points
from src.rendering.projection import Projector
from src.simulation.playback import Location, PlaybackSnapshot, VisualDrone


class Renderer:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.padding: int = 2

    def render(
        self,
        size: ContentSize,
        frame: AnimationFrame | None = None,
        playback: PlaybackSnapshot | None = None,
    ) -> list[str]:
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
        self._draw_zones(canvas, projector, frame)
        if playback is not None:
            self._draw_drones(canvas, projector, playback, frame)

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
                canvas.set(x, y, style("·", bold=True))

    def _draw_zones(
        self,
        canvas: Canvas,
        projector: Projector,
        frame: AnimationFrame | None,
    ) -> None:
        elapsed = frame.elapsed if frame is not None else 0.0
        animated_color = rainbow_color(elapsed)
        for zone in self.graph.zones.values():
            color = self._zone_color(zone.name, animated_color)

            x, y = self._project(projector, zone.x, zone.y)
            canvas.set(x, y, style("●", foreground=color, bold=True))

    def _zone_color(
        self, zone_name: str, animated_color: tuple[int, int, int]
    ) -> TextColor:
        color = self.graph.zones[zone_name].metadata.color
        if color == "rainbow":
            return animated_color
        return color if color is not None else "white"

    def _draw_drones(
        self,
        canvas: Canvas,
        projector: Projector,
        playback: PlaybackSnapshot,
        frame: AnimationFrame | None,
    ) -> None:
        elapsed = frame.elapsed if frame is not None else 0.0
        rainbow = rainbow_color(elapsed)
        groups: dict[tuple[int, int], list[int]] = {}
        colors: dict[tuple[int, int], TextColor] = {}
        for drone_id, visual in playback.positions.items():
            position = self._visual_position(projector, visual)
            groups.setdefault(position, []).append(drone_id)
            zone_name = self._visible_zone(visual)
            if zone_name is not None:
                colors[position] = self._zone_color(zone_name, rainbow)
            elif position not in colors:
                source = visual.start.source or visual.start.zone
                colors[position] = self._zone_color(
                    source or self.graph.start_hub.name, rainbow
                )

        for (x, y), drone_ids in groups.items():
            label = (
                f"D{drone_ids[0]}" if len(drone_ids) == 1
                else f"x{len(drone_ids)}"
            )
            label = label[:canvas.width]
            left = max(0, min(x - len(label) // 2, canvas.width - len(label)))
            blink = (
                playback.selected_drone_id in drone_ids
                and frame is not None
                and int(elapsed * 2) % 2 == 0
            )
            for index, char in enumerate(label):
                canvas.set(
                    left + index, y,
                    style(char, foreground=colors[(x, y)], bold=True,
                          reverse=blink),
                )

    def _visual_position(
        self, projector: Projector, visual: VisualDrone
    ) -> tuple[int, int]:
        start = self._location_position(projector, visual.start)
        end = self._location_position(projector, visual.end)
        points = get_line_points(start, end)
        return points[round(visual.progress * (len(points) - 1))]

    def _location_position(
        self, projector: Projector, location: Location
    ) -> tuple[int, int]:
        if location.zone is not None:
            zone = self.graph.zones[location.zone]
            return self._project(projector, zone.x, zone.y)
        if location.source is None or location.target is None:
            raise ValueError("Connection location needs both endpoint zones")
        source = self.graph.zones[location.source]
        target = self.graph.zones[location.target]
        points = get_line_points(
            self._project(projector, source.x, source.y),
            self._project(projector, target.x, target.y),
        )
        return points[(len(points) - 1) // 2]

    @staticmethod
    def _visible_zone(visual: VisualDrone) -> str | None:
        if visual.progress == 0:
            return visual.start.zone
        if visual.progress == 1:
            return visual.end.zone
        return None

    def _project(
        self,
        projector: Projector,
        x: int,
        y: int,
    ) -> tuple[int, int]:
        screen_x, screen_y = projector.project(x, y)
        return (
            screen_x + self.padding,
            screen_y + self.padding,
        )
