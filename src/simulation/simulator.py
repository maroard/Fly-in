from src.domain import Graph, Drone, Zone, Connection
from src.simulation import SimulationState, Turn, Movement, MoveIntent
from src.pathfinding.pathfinder import PathFinder


class Simulator:
    def __init__(self, graph: Graph) -> None:
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
        self.path = PathFinder(self.graph).find_shortest_path()

    def simulate(self) -> None:
        while not all(drone.delivered for drone in self.state.drones):
            self.step()

    def step(self) -> Turn:
        turn = Turn(len(self.state.turns) + 1)

        if self.path is None:
            raise RuntimeError("Aucun chemin trouvé")

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

        self.state.turns.append(turn)
        return turn

    def _get_zone_occupancy(self, zone: Zone) -> int:
        occupancy: int = 0
        for drone in self.state.drones:
            if drone.zone == zone:
                occupancy += 1

        return occupancy

    def _get_connection_occupancy(self, connection: Connection) -> int:
        occupancy: int = 0
        for drone in self.state.drones:
            if drone.connection == connection:
                occupancy += 1

        return occupancy
