from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain import Connection, Drone, Graph, Zone
from src.pathfinding.path import Path
from src.pathfinding.pathfinder import PathFinder

if TYPE_CHECKING:
    from src.simulation.move_intent import (
        BlockingResource,
        MoveIntent,
        RejectedIntent,
    )
    from src.simulation.move_intent_resolver import MoveIntentResolver


class Router:
    """Assign paths and reroute drones around rejected movements."""

    def __init__(
        self,
        graph: Graph,
        drones: list[Drone],
        resolver: MoveIntentResolver,
    ) -> None:
        self.graph = graph
        self.drones = drones
        self.resolver = resolver
        self.path_finder = PathFinder(graph)

        initial_path = self.path_finder.find_shortest_path()
        if initial_path is None:
            raise RuntimeError("No valid path for this graph.")

        self.drone_paths: dict[int, Path] = {
            drone.id: initial_path
            for drone in drones
        }

    def build_move_intents(
        self,
        excluded_drone_ids: set[int],
    ) -> list[MoveIntent]:
        """Build desired moves for drones that may move this turn."""
        from src.simulation.move_intent import MoveIntent

        move_intents: list[MoveIntent] = []

        for drone in self.drones:
            if drone.id in excluded_drone_ids:
                continue

            if drone.delivered:
                continue

            if drone.zone is None:
                raise RuntimeError(
                    f"Drone {drone.id} must be on a zone to build a move "
                    "intent."
                )

            if drone.zone == self.graph.end_hub:
                raise RuntimeError(
                    f"Drone {drone.id} is on the end hub but is not marked "
                    "as delivered."
                )

            drone_path = self.drone_paths[drone.id]
            next_zone_name = drone_path.get_next_zone_name(
                drone.zone.name
            )

            if next_zone_name is None:
                raise RuntimeError(
                    f"Path has no next zone for drone {drone.id} from "
                    f"'{drone.zone.name}'."
                )

            destination = self.graph.zones.get(next_zone_name)
            if destination is None:
                raise RuntimeError(
                    f"Path references unknown zone '{next_zone_name}'."
                )

            move_intents.append(
                MoveIntent(drone, destination)
            )

        return move_intents

    def reroute_rejected_intents(
        self,
        rejected_intents: list[RejectedIntent],
        accepted_intents: list[MoveIntent],
    ) -> list[MoveIntent]:
        """Reroute blocked drones when moving now is cheaper than waiting."""
        rerouted_intents: list[MoveIntent] = []
        protected_intents = accepted_intents.copy()

        for rejection in rejected_intents:
            new_intent = self._find_rerouted_intent(
                rejection,
                protected_intents,
            )

            if new_intent is None:
                continue

            rerouted_intents.append(new_intent)
            protected_intents.append(new_intent)

        return rerouted_intents

    def _find_rerouted_intent(
        self,
        rejected_intent: RejectedIntent,
        accepted_intents: list[MoveIntent],
    ) -> MoveIntent | None:
        """Find a cheaper immediately usable alternative for one drone."""
        from src.simulation.move_intent import MoveIntent

        drone = rejected_intent.intent.drone
        current_zone = drone.zone

        if current_zone is None:
            raise RuntimeError(
                f"Drone {drone.id} must be on a zone to reroute."
            )

        current_path = self.drone_paths[drone.id]
        wait_cost = (
            self._get_remaining_path_cost(current_path, current_zone)
            + 1
        )

        excluded_zones: list[Zone] = []
        excluded_connections: list[Connection] = []
        self._exclude_blocking_resource(
            rejected_intent.blocked_by,
            excluded_zones,
            excluded_connections,
        )

        max_attempts = (
            len(self.graph.zones)
            + len(self.graph.connections)
        )

        for _ in range(max_attempts):
            alternative_path = self.path_finder.find_shortest_path(
                start_zone=current_zone,
                excluded_zones=excluded_zones,
                excluded_connections=excluded_connections,
            )

            if alternative_path is None:
                return None

            alternative_cost = self._get_remaining_path_cost(
                alternative_path,
                current_zone,
            )

            if alternative_cost >= wait_cost:
                return None

            next_zone_name = alternative_path.get_next_zone_name(
                current_zone.name
            )
            if next_zone_name is None:
                return None

            destination = self.graph.zones[next_zone_name]
            alternative_intent = MoveIntent(drone, destination)
            self.resolver.validate_intent(alternative_intent)

            blocker = self.resolver.blocking_resource(
                alternative_intent,
                accepted_intents,
            )

            if blocker is None:
                self.drone_paths[drone.id] = alternative_path
                return alternative_intent

            if not self._exclude_blocking_resource(
                blocker,
                excluded_zones,
                excluded_connections,
            ):
                return None

        return None

    def _exclude_blocking_resource(
        self,
        resource: BlockingResource,
        excluded_zones: list[Zone],
        excluded_connections: list[Connection],
    ) -> bool:
        """Add a blocking resource to pathfinding exclusions once."""
        if isinstance(resource, Connection):
            if resource in excluded_connections:
                return False

            excluded_connections.append(resource)
            return True

        if resource in excluded_zones:
            return False

        excluded_zones.append(resource)
        return True

    def _get_remaining_path_cost(
        self,
        path: Path,
        current_zone: Zone,
    ) -> int:
        """Return the movement cost from a current zone to path end."""
        try:
            current_index = path.zones.index(current_zone.name)
        except ValueError as error:
            raise RuntimeError(
                f"Path assigned to a drone does not contain current zone "
                f"'{current_zone.name}'."
            ) from error

        cost = 0

        for zone_name in path.zones[current_index + 1:]:
            zone = self.graph.zones[zone_name]

            if zone.metadata.zone_type == "restricted":
                cost += 2
            else:
                cost += 1

        return cost
