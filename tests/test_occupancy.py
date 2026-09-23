from src.domain.connection import Connection, ConnectionMetadata
from src.domain.drone import Drone
from src.domain.occupancy import Occupancy
from src.domain.zone import Zone


def test_counts_default_to_zero_and_links_are_undirected() -> None:
    occupancy = Occupancy()
    assert occupancy.zone_occupancy("a") == 0
    assert not occupancy.is_zone_occupied("a")
    assert occupancy.connection_occupancy("a", "b") == 0
    assert not occupancy.is_connection_occupied("b", "a")
    occupancy.zones["a"] = 2
    occupancy.connections[("a", "b")] = 3
    assert occupancy.zone_occupancy("a") == 2
    assert occupancy.is_zone_occupied("a")
    assert occupancy.connection_occupancy("b", "a") == 3
    assert occupancy.is_connection_occupied("b", "a")


def test_refresh_replaces_counts_from_current_drone_positions() -> None:
    a = Zone(name="a", x=0, y=0)
    b = Zone(name="b", x=1, y=0)
    link = Connection("b", "a", ConnectionMetadata())
    first, second = Drone(1, a), Drone(2, a)
    occupancy = Occupancy()
    occupancy.refresh([first, second])
    assert occupancy.zone_occupancy("a") == 2
    first.start_transit(link, b)
    occupancy.refresh([first, second])
    assert occupancy.zone_occupancy("a") == 1
    assert occupancy.zone_occupancy("b") == 0
    assert occupancy.connection_occupancy("a", "b") == 1
    first.arrive()
    first.deliver()
    occupancy.refresh([first, second])
    assert occupancy.zone_occupancy("b") == 1
    assert not occupancy.is_connection_occupied("a", "b")
    occupancy.refresh([])
    assert occupancy.zones == {}
    assert occupancy.connections == {}


def test_simulator_updates_shared_occupancy_after_arrival() -> None:
    from src.domain.graph import Graph
    from src.parsing.map_config import MapConfig
    from src.simulation.simulator import Simulator

    a = Zone(name="a", x=0, y=0)
    b = Zone(name="b", x=1, y=0)
    link = Connection("a", "b", ConnectionMetadata())
    graph = Graph(MapConfig(2, a, b, {"a": a, "b": b}, [link]))
    occupancy = Occupancy({}, {})
    simulator = Simulator(graph, occupancy=occupancy)
    assert simulator.occupancy is occupancy
    assert occupancy.zone_occupancy("a") == 2
    simulator.state.drones[0].start_transit(link, b)
    simulator.step()
    assert occupancy.zone_occupancy("a") == 1
    assert occupancy.zone_occupancy("b") == 1
    assert not occupancy.is_connection_occupied("a", "b")
    assert simulator._get_zone_occupancy(a) == 1
    assert simulator._get_connection_occupancy(link) == 0


def test_run_shares_occupancy_with_renderer() -> None:
    from src.application import Application
    from src.domain.graph import Graph
    from src.parsing.map_config import MapConfig
    from src.rendering.renderer import Renderer
    from tuiloom import CommandContext, ContentSize

    a = Zone(name="a", x=0, y=0)
    b = Zone(name="b", x=1, y=0)
    link = Connection("a", "b", ConnectionMetadata())
    application = Application()
    application.graph = Graph(
        MapConfig(2, a, b, {"a": a, "b": b}, [link])
    )
    application.renderer = Renderer(application.graph)
    command = next(
        c for c in application.main_menu.commands
        if c.label == "Run simulation"
    )
    context = CommandContext(
        application.terminal_app, application.main_menu, command, None
    )
    command.behavior(context)
    simulator = application.simulator
    assert simulator is not None
    assert application.renderer.occupancy is simulator.occupancy
    assert application.renderer.occupancy.zone_occupancy("a") == 2
    assert application.renderer.render(ContentSize(40, 20))
    command.behavior(context)
    assert application.simulator is simulator


def test_run_without_path_leaves_occupancy_unchanged() -> None:
    from src.application import Application
    from src.domain.graph import Graph
    from src.parsing.map_config import MapConfig
    from src.rendering.renderer import Renderer
    from tuiloom import CommandContext

    a = Zone(name="a", x=0, y=0)
    b = Zone(name="b", x=1, y=0)
    application = Application()
    application.renderer = Renderer(
        Graph(MapConfig(1, a, b, {"a": a, "b": b}, []))
    )
    command = application.main_menu.commands[0]
    command.behavior(CommandContext(
        application.terminal_app, application.main_menu, command, None
    ))
    assert application.simulator is None
    assert application.renderer.occupancy.zones == {}
    assert application.main_menu._alert_text == "No valid path for this graph."
