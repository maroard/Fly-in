from src.domain import Drone, Graph
from src.domain.occupancy import Occupancy
from src.pathfinding.router import Router
from src.pathfinding.routing_mode import RoutingMode
from src.simulation.move_intent import MoveIntent
from src.simulation.move_intent_resolver import MoveIntentResolver
from src.simulation.state import SimulationState
from src.simulation.turn import Movement, Turn


class Simulator:
    """Run a Fly-in simulation while enforcing movement constraints."""

    def __init__(
        self,
        graph: Graph,
        routing_mode: RoutingMode = "single-path",
    ) -> None:
        """Initialize drones, routing and occupancy tracking."""
        if routing_mode not in ("single-path", "multi-path"):
            raise ValueError(f"Unknown routing mode: '{routing_mode}'.")

        self.graph = graph
        self.mode = routing_mode
        self.state = SimulationState(
            drones=[
                Drone(
                    drone_id=i + 1,
                    start_zone=graph.start_hub,
                )
                for i in range(graph.nb_drones)
            ]
        )
        self.occupancy = Occupancy()
        self.resolver = MoveIntentResolver(
            self.graph, self.state.drones, self.occupancy
        )
        self.router = Router(self.graph, self.state.drones, self.resolver)
        self.path_finder = self.router.path_finder
        self.drone_paths = self.router.drone_paths
        self.occupancy.refresh(self.state.drones)

    def simulate(self) -> None:
        """Run turns until every drone reaches the end hub."""
        while not all(drone.delivered for drone in self.state.drones):
            turn = self.step()

            remaining_drones = sum(
                1
                for drone in self.state.drones
                if not drone.delivered
            )

            if not turn.movements and remaining_drones > 0:
                raise RuntimeError(
                    f"Simulation deadlock at turn {turn.number}: "
                    f"no drone moved while {remaining_drones} drone(s) "
                    "remain undelivered."
                )

    def step(self) -> Turn:
        """Execute exactly one simulation turn."""
        turn = Turn(len(self.state.turns) + 1)

        moved_drone_ids = self._advance_transits(turn)

        move_intents = self.router.build_move_intents(
            excluded_drone_ids=moved_drone_ids
        )
        accepted_intents, rejected_intents = self.resolver.resolve(
            move_intents
        )

        if self.mode == "multi-path":
            rerouted_intents = self.router.reroute_rejected_intents(
                rejected_intents,
                accepted_intents,
            )
            accepted_intents.extend(rerouted_intents)

        self._apply_move_intents(accepted_intents, turn)
        self.occupancy.refresh(self.state.drones)

        self.state.turns.append(turn)
        return turn

    def _advance_transits(self, turn: Turn) -> set[int]:
        """Complete restricted-zone transits started previously."""
        moved_drone_ids: set[int] = set()

        for drone in self.state.drones:
            if drone.connection is None:
                continue

            drone.arrive()

            if drone.zone is None:
                raise RuntimeError(
                    f"Drone {drone.id} has no zone after completing transit."
                )

            turn.movements.append(
                Movement(drone.id, drone.zone.name)
            )
            moved_drone_ids.add(drone.id)

            if drone.zone == self.graph.end_hub:
                drone.deliver()

        return moved_drone_ids

    def _apply_move_intents(
        self,
        move_intents: list[MoveIntent],
        turn: Turn,
    ) -> None:
        """Apply accepted movements and append their turn output."""
        for move_intent in move_intents:
            drone = move_intent.drone
            destination = move_intent.destination
            current_zone = drone.zone

            if current_zone is None:
                raise RuntimeError(
                    f"Drone {drone.id} must be on a zone before moving."
                )

            if destination.metadata.zone_type == "restricted":
                connection = self.graph.get_connection(
                    current_zone,
                    destination,
                )
                drone.start_transit(
                    connection=connection,
                    target_zone=destination,
                )

                connection_name = (
                    f"{connection.zone_name1}-{connection.zone_name2}"
                )
                turn.movements.append(
                    Movement(drone.id, connection_name)
                )
                continue

            drone.move_to(destination)
            turn.movements.append(
                Movement(drone.id, destination.name)
            )

            if drone.zone == self.graph.end_hub:
                drone.deliver()
