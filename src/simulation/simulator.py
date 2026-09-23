from src.domain import Graph, Drone, Zone, Connection
from src.domain.occupancy import Occupancy
from src.simulation import SimulationState, Turn, Movement
from src.pathfinding.pathfinder import PathFinder


class Simulator:
    def __init__(
        self, graph: Graph, occupancy: Occupancy | None = None
    ) -> None:
        self.graph = graph
        self.state = SimulationState(
            drones=[
                Drone(
                    drone_id=i + 1,
                    start_zone=graph.start_hub
                )
                for i in range(graph.nb_drones)
            ]
        )
        self.occupancy = occupancy if occupancy is not None else Occupancy()
        path = PathFinder(self.graph).find_shortest_path()
        if path is None:
            raise RuntimeError("No valid path for this graph.")
        self.path = path
        self.occupancy.refresh(self.state.drones)

    def simulate(self) -> None:
        while not all(drone.delivered for drone in self.state.drones):
            self.step()

    def step(self) -> Turn:
        turn = Turn(len(self.state.turns) + 1)

        destination_name = self.path.zones[turn.number]
        destination = self.graph.zones[destination_name]

        for drone in self.state.drones:
            if drone.delivered:
                continue

            drone.move_to(destination)
            turn.movements.append(
                Movement(drone.id, destination.name)
            )

            if drone.zone == self.graph.end_hub:
                drone.deliver()

        self.occupancy.refresh(self.state.drones)
        self.state.turns.append(turn)
        return turn

    def _get_zone_occupancy(self, zone: Zone) -> int:
        self.occupancy.refresh(self.state.drones)
        return self.occupancy.zone_occupancy(zone.name)

    def _get_connection_occupancy(self, connection: Connection) -> int:
        self.occupancy.refresh(self.state.drones)
        return self.occupancy.connection_occupancy(
            connection.zone_name1, connection.zone_name2
        )
