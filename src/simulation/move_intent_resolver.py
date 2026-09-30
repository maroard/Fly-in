from src.domain import Connection, Drone, Graph, Zone
from src.domain.occupancy import Occupancy
from src.simulation.move_intent import (
    BlockingResource,
    MoveIntent,
    RejectedIntent,
)


class MoveIntentResolver:
    """Validate and resolve movement conflicts for one simulation state."""

    def __init__(
        self,
        graph: Graph,
        drones: list[Drone],
        occupancy: Occupancy,
    ) -> None:
        self.graph = graph
        self.drones = drones
        self.occupancy = occupancy

    def resolve(
        self,
        move_intents: list[MoveIntent],
    ) -> tuple[list[MoveIntent], list[RejectedIntent]]:
        """Resolve movement conflicts and keep their rejection causes."""
        for move_intent in move_intents:
            self.validate_intent(move_intent)

        accepted_intents = move_intents.copy()
        rejected_intents: list[RejectedIntent] = []

        while True:
            previous_count = len(accepted_intents)

            accepted_intents = self._resolve_connection_capacities(
                accepted_intents,
                rejected_intents,
            )
            accepted_intents = self._resolve_restricted_reservations(
                accepted_intents,
                rejected_intents,
            )
            accepted_intents = self._resolve_zone_capacities(
                accepted_intents,
                rejected_intents,
            )

            if len(accepted_intents) == previous_count:
                break

        return accepted_intents, rejected_intents

    def validate_intent(self, move_intent: MoveIntent) -> None:
        """Validate invariant and graph rules for one movement."""
        drone = move_intent.drone
        destination = move_intent.destination
        source = drone.zone

        if drone.delivered:
            raise RuntimeError(
                f"Delivered drone {drone.id} cannot have a move intent."
            )

        if source is None:
            raise RuntimeError(
                f"Drone {drone.id} must be on a zone to have a move intent."
            )

        if source == destination:
            raise RuntimeError(
                f"Drone {drone.id} cannot move from '{source.name}' to "
                "the same zone."
            )

        if destination.metadata.zone_type == "blocked":
            raise RuntimeError(
                f"Drone {drone.id} cannot enter blocked zone "
                f"'{destination.name}'."
            )

        try:
            self.graph.get_connection(source, destination)
        except ValueError as error:
            raise RuntimeError(
                f"Drone {drone.id} cannot move from '{source.name}' to "
                f"'{destination.name}': the zones are not connected."
            ) from error

    def _resolve_connection_capacities(
        self,
        move_intents: list[MoveIntent],
        rejected_intents: list[RejectedIntent],
    ) -> list[MoveIntent]:
        """Reject movements exceeding connection capacities."""
        accepted_intents = move_intents.copy()

        for connection in self.graph.connections:
            connection_intents = [
                intent
                for intent in accepted_intents
                if self._intent_uses_connection(intent, connection)
            ]

            overflow = (
                len(connection_intents)
                - connection.metadata.max_link_capacity
            )

            if overflow <= 0:
                continue

            rejected = sorted(
                connection_intents,
                key=lambda intent: intent.drone.id,
                reverse=True,
            )[:overflow]

            for intent in rejected:
                accepted_intents.remove(intent)
                rejected_intents.append(
                    RejectedIntent(
                        intent=intent,
                        blocked_by=connection,
                    )
                )

        return accepted_intents

    def _intent_uses_connection(
        self,
        move_intent: MoveIntent,
        connection: Connection,
    ) -> bool:
        """Return whether an intent traverses a connection."""
        source = move_intent.drone.zone

        if source is None:
            raise RuntimeError(
                f"Drone {move_intent.drone.id} must be on a zone to have "
                "a move intent."
            )

        destination = move_intent.destination

        return (
            source.name == connection.zone_name1
            and destination.name == connection.zone_name2
        ) or (
            source.name == connection.zone_name2
            and destination.name == connection.zone_name1
        )

    def _resolve_restricted_reservations(
        self,
        move_intents: list[MoveIntent],
        rejected_intents: list[RejectedIntent],
    ) -> list[MoveIntent]:
        """Reserve capacity for drones entering restricted zones."""
        accepted_intents = move_intents.copy()

        for zone in self.graph.zones.values():
            if zone.metadata.zone_type != "restricted":
                continue

            if zone in (
                self.graph.start_hub,
                self.graph.end_hub,
            ):
                continue

            current_occupancy = self.zone_occupancy(zone)

            leaving_intents = [
                intent
                for intent in accepted_intents
                if intent.drone.zone == zone
            ]
            reservation_intents = [
                intent
                for intent in accepted_intents
                if intent.destination == zone
            ]

            occupancy_after_departures = (
                current_occupancy - len(leaving_intents)
            )
            available_slots = (
                zone.metadata.max_drones
                - occupancy_after_departures
            )
            overflow = (
                len(reservation_intents)
                - max(0, available_slots)
            )

            if overflow <= 0:
                continue

            rejected = sorted(
                reservation_intents,
                key=lambda intent: intent.drone.id,
                reverse=True,
            )[:overflow]

            for intent in rejected:
                accepted_intents.remove(intent)
                rejected_intents.append(
                    RejectedIntent(
                        intent=intent,
                        blocked_by=zone,
                    )
                )

        return accepted_intents

    def _resolve_zone_capacities(
        self,
        move_intents: list[MoveIntent],
        rejected_intents: list[RejectedIntent],
    ) -> list[MoveIntent]:
        """Reject movements exceeding zone capacities this turn."""
        accepted_intents = move_intents.copy()

        for zone in self.graph.zones.values():
            if zone in (
                self.graph.start_hub,
                self.graph.end_hub,
            ):
                continue

            current_occupancy = self.zone_occupancy(zone)

            leaving_intents = [
                intent
                for intent in accepted_intents
                if intent.drone.zone == zone
            ]
            entering_intents = [
                intent
                for intent in accepted_intents
                if (
                    intent.destination == zone
                    and zone.metadata.zone_type != "restricted"
                )
            ]

            projected_occupancy = (
                current_occupancy
                - len(leaving_intents)
                + len(entering_intents)
            )
            overflow = (
                projected_occupancy
                - zone.metadata.max_drones
            )

            if overflow <= 0:
                continue

            rejected = sorted(
                entering_intents,
                key=lambda intent: intent.drone.id,
                reverse=True,
            )[:overflow]

            for intent in rejected:
                accepted_intents.remove(intent)
                rejected_intents.append(
                    RejectedIntent(
                        intent=intent,
                        blocked_by=zone,
                    )
                )

        return accepted_intents

    def blocking_resource(
        self,
        move_intent: MoveIntent,
        accepted_intents: list[MoveIntent],
    ) -> BlockingResource | None:
        """Return what prevents an extra intent from being accepted."""
        drone = move_intent.drone
        source = drone.zone
        destination = move_intent.destination

        if source is None:
            raise RuntimeError(
                f"Drone {drone.id} must be on a zone to test a movement."
            )

        connection = self.graph.get_connection(source, destination)
        connection_usage = sum(
            1
            for intent in accepted_intents
            if self._intent_uses_connection(intent, connection)
        )

        if (
            connection_usage + 1
            > connection.metadata.max_link_capacity
        ):
            return connection

        if destination in (
            self.graph.start_hub,
            self.graph.end_hub,
        ):
            return None

        current_occupancy = self.zone_occupancy(destination)
        leaving_count = sum(
            1
            for intent in accepted_intents
            if intent.drone.zone == destination
        )

        if destination.metadata.zone_type == "restricted":
            reservation_count = sum(
                1
                for intent in accepted_intents
                if intent.destination == destination
            )
            occupancy_after_departures = (
                current_occupancy - leaving_count
            )
            available_slots = (
                destination.metadata.max_drones
                - occupancy_after_departures
            )

            if reservation_count + 1 > max(0, available_slots):
                return destination

            return None

        entering_count = sum(
            1
            for intent in accepted_intents
            if (
                intent.destination == destination
                and destination.metadata.zone_type != "restricted"
            )
        )
        projected_occupancy = (
            current_occupancy
            - leaving_count
            + entering_count
            + 1
        )

        if projected_occupancy > destination.metadata.max_drones:
            return destination

        return None

    def zone_occupancy(self, zone: Zone) -> int:
        """Return the current number of drones occupying a zone."""
        self.occupancy.refresh(self.drones)
        return self.occupancy.zone_occupancy(zone.name)
