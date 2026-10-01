from pathlib import Path

from src.domain.graph import Graph
from src.parsing.parser import Parser
from src.simulation.playback import Playback
from src.simulation.turn import Movement, Turn
from src.rendering.renderer import Renderer
from tuiloom import AnimationFrame, ContentSize, style
import re


def graph() -> Graph:
    return Graph(Parser(Path("maps/easy/01_linear_path.txt")).process())


def test_one_shot_animates_turn_then_advances_page() -> None:
    playback = Playback(
        graph(),
        [Turn(1, [Movement(1, "waypoint1"), Movement(2, "waypoint1")]),
         Turn(2, [Movement(1, "waypoint2")])],
        "one_shot", 1.0,
    )
    playback.advance(0.0)
    assert playback.turn_index == 0
    assert playback.snapshot().positions[1].progress == 0.0
    playback.advance(0.5)
    assert playback.snapshot().positions[1].progress == 0.5
    assert playback.snapshot().positions[2].progress == 0.5
    playback.advance(1.0)
    assert playback.turn_index == 1
    assert playback.completed_movements == 2
    playback.advance(2.0)
    assert playback.finished
    assert playback.turn_index == 1


def test_step_mode_waits_for_each_space() -> None:
    playback = Playback(
        graph(),
        [Turn(1, [Movement(1, "waypoint1"), Movement(2, "waypoint1")])],
        "step_by_step", 1.0,
    )
    playback.advance(0.0)
    assert playback.snapshot().positions[1].start.zone == "start"
    assert playback.start_next_movement()
    assert not playback.start_next_movement()
    playback.advance(0.5)
    assert playback.snapshot().positions[1].progress == 0.5
    assert playback.snapshot().positions[2].progress == 1.0
    playback.advance(1.0)
    assert playback.completed_movements == 1
    assert playback.start_next_movement()
    playback.advance(2.0)
    assert playback.finished


def test_restricted_move_stops_at_midpoint_until_next_turn() -> None:
    from src.domain.connection import Connection, ConnectionMetadata
    from src.domain.zone import Zone, ZoneMetadata
    from src.parsing.map_config import MapConfig

    start = Zone(name="start", x=0, y=0)
    end = Zone(name="end", x=10, y=0,
               metadata=ZoneMetadata(zone_type="restricted", color="red"))
    link = Connection("start", "end", ConnectionMetadata())
    graph = Graph(
        MapConfig(1, start, end, {"start": start, "end": end}, [link])
    )
    playback = Playback(graph, [
        Turn(1, [Movement(1, "start-end")]),
        Turn(2, [Movement(1, "end")]),
    ], "one_shot", 1.0)
    playback.advance(0.0)
    playback.advance(1.0)
    midpoint = playback.snapshot().positions[1]
    assert midpoint.start.connection == "start-end"
    assert midpoint.start.source == "start"
    assert midpoint.start.target == "end"
    rendered = Renderer(graph).render(
        ContentSize(40, 10), AnimationFrame(1.0, 20),
        playback.snapshot(),
    )
    plain = re.sub(r"\x1b\[[0-9;]*m", "", "\n".join(rendered))
    assert 15 <= plain.splitlines()[5].index("D1") <= 23
    playback.advance(2.0)
    assert playback.snapshot().positions[1].end.zone == "end"


def test_graph_draws_groups_and_moving_drone_with_zone_color() -> None:
    from src.domain.connection import Connection, ConnectionMetadata
    from src.domain.zone import Zone, ZoneMetadata
    from src.parsing.map_config import MapConfig

    start = Zone(name="start", x=0, y=0, metadata=ZoneMetadata(color="red"))
    end = Zone(name="end", x=10, y=0, metadata=ZoneMetadata(color="blue"))
    link = Connection("start", "end", ConnectionMetadata())
    graph = Graph(
        MapConfig(2, start, end, {"start": start, "end": end}, [link])
    )
    playback = Playback(
        graph, [Turn(1, [Movement(1, "end")])], "one_shot", 1.0
    )
    renderer = Renderer(graph)
    playback.advance(0.0)
    initial = "\n".join(renderer.render(
        ContentSize(40, 10), AnimationFrame(0.0, 0), playback.snapshot()
    ))
    assert "x2" in re.sub(r"\x1b\[[0-9;]*m", "", initial)
    assert style("x", foreground="red", bold=True) in initial
    playback.advance(0.5)
    middle = "\n".join(renderer.render(
        ContentSize(40, 10), AnimationFrame(0.5, 5), playback.snapshot()
    ))
    plain = re.sub(r"\x1b\[[0-9;]*m", "", middle)
    assert "D1" in plain
    assert "D2" in plain
    playback.select_drone(1)
    highlighted = "\n".join(renderer.render(
        ContentSize(40, 10), AnimationFrame(0.1, 1), playback.snapshot()
    ))
    assert re.search(r"\x1b\[[0-9;]*7[0-9;]*m", highlighted)


def test_graph_shows_group_at_restricted_connection_midpoint() -> None:
    from src.domain.connection import Connection, ConnectionMetadata
    from src.domain.zone import Zone, ZoneMetadata
    from src.parsing.map_config import MapConfig

    start = Zone(name="start", x=0, y=0)
    end = Zone(
        name="end", x=10, y=0,
        metadata=ZoneMetadata(zone_type="restricted"),
    )
    link = Connection(
        "start", "end", ConnectionMetadata(max_link_capacity=2)
    )
    graph = Graph(
        MapConfig(2, start, end, {"start": start, "end": end}, [link])
    )
    playback = Playback(graph, [Turn(1, [
        Movement(1, "start-end"), Movement(2, "start-end"),
    ])], "one_shot", 1.0)
    playback.advance(0.0)
    playback.advance(1.0)
    rendered = Renderer(graph).render(
        ContentSize(40, 10), AnimationFrame(1.0, 20),
        playback.snapshot(),
    )
    plain = re.sub(r"\x1b\[[0-9;]*m", "", "\n".join(rendered))
    assert "x2" in plain.splitlines()[5]


def test_replay_uses_row_order_without_changing_metrics() -> None:
    playback = Playback(graph(), [
        Turn(1, [Movement(1, "waypoint1"), Movement(2, "waypoint1")]),
        Turn(2, [Movement(1, "waypoint2")]),
    ], "one_shot", 1.0)
    playback.advance(0.0)
    playback.advance(2.0)
    assert playback.finished
    final_positions = playback.snapshot().positions
    final_metrics = (playback.turn_index, playback.completed_movements)

    playback.select_movement(0, 0)
    first = playback.snapshot()
    assert first.positions[1].end.zone == "waypoint1"
    assert first.positions[2].end.zone == "start"
    assert first.selected_drone_id == 1

    playback.select_movement(0, 1)
    second = playback.snapshot()
    assert second.positions[1].end.zone == "waypoint1"
    assert second.positions[2].end.zone == "waypoint1"
    assert second.selected_drone_id == 2

    playback.select_movement(1, 0)
    assert playback.snapshot().positions[1].end.zone == "waypoint2"
    assert (playback.turn_index, playback.completed_movements) == final_metrics
    playback.clear_replay()
    assert playback.snapshot().positions == final_positions
    assert playback.snapshot().selected_drone_id is None


def test_replay_keeps_restricted_midpoint_until_arrival() -> None:
    from src.domain.connection import Connection, ConnectionMetadata
    from src.domain.zone import Zone, ZoneMetadata
    from src.parsing.map_config import MapConfig

    start = Zone(name="start", x=0, y=0)
    end = Zone(name="end", x=10, y=0,
               metadata=ZoneMetadata(zone_type="restricted"))
    link = Connection("start", "end", ConnectionMetadata())
    restricted = Graph(MapConfig(
        1, start, end, {"start": start, "end": end}, [link]
    ))
    playback = Playback(restricted, [
        Turn(1, [Movement(1, "start-end")]),
        Turn(2, [Movement(1, "end")]),
    ], "step_by_step", 1.0)
    playback.advance(0.0)
    assert playback.start_next_movement()
    playback.advance(1.0)
    assert playback.start_next_movement()
    playback.advance(2.0)

    playback.select_movement(0, 0)
    midpoint = playback.snapshot().positions[1]
    assert midpoint.start.connection == "start-end"
    assert midpoint.start.source == "start"
    assert midpoint.start.target == "end"
    playback.select_movement(1, 0)
    assert playback.snapshot().positions[1].end.zone == "end"


def test_replayed_group_blinks_for_selected_drone() -> None:
    playback = Playback(graph(), [Turn(1, [
        Movement(1, "waypoint1"), Movement(2, "waypoint1"),
    ])], "one_shot", 1.0)
    playback.advance(0.0)
    playback.advance(1.0)
    playback.select_movement(0, 1)
    rendered = "\n".join(Renderer(playback.graph).render(
        ContentSize(40, 10), AnimationFrame(2.0, 40), playback.snapshot()
    ))
    assert "x2" in re.sub(r"\x1b\[[0-9;]*m", "", rendered)
    assert re.search(r"\x1b\[[0-9;]*7[0-9;]*m", rendered)
