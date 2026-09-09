from src.domain import Graph, Drone, Zone
from src.simulation import SimulationState, Turn, Movement



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

    def step(self) -> None:
        pass

    def _get_zone_occupancy(self, zone: )