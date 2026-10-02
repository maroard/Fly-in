"""Count drones currently occupying zones and connections."""

from collections.abc import Iterable
from dataclasses import dataclass, field

from src.domain.drone import Drone


@dataclass
class Occupancy:
    """Share a snapshot of drone positions without simulation dependencies.

    Connections are undirected. Delivered drones still count while they
    retain a zone. Refresh after position changes; target zones are not
    reservations.

    Attributes:
        zones: Drone counts indexed by occupied zone name.
        connections: Drone counts indexed by sorted endpoint-name pairs.
    """

    zones: dict[str, int] = field(default_factory=dict)
    connections: dict[tuple[str, str], int] = field(default_factory=dict)

    def zone_occupancy(self, zone_name: str) -> int:
        """Return the stored number of drones on a zone.

        Args:
            zone_name: Name of the zone to inspect.

        Returns:
            Recorded count, or zero if the zone has no stored entry.
        """
        return self.zones.get(zone_name, 0)

    def connection_occupancy(self, zone1: str, zone2: str) -> int:
        """Return the stored number of drones on an undirected connection.

        Args:
            zone1: Name of the first endpoint zone.
            zone2: Name of the second endpoint zone.

        Returns:
            Recorded count, independent of endpoint order, or zero.
        """
        key = (min(zone1, zone2), max(zone1, zone2))

        return self.connections.get(key, 0)

    def is_zone_occupied(self, zone_name: str) -> bool:
        """Check whether a zone has at least one recorded drone.

        Args:
            zone_name: Name of the zone to inspect.

        Returns:
            True if the stored zone occupancy is greater than zero.
        """
        return self.zone_occupancy(zone_name) > 0

    def is_connection_occupied(self, zone1: str, zone2: str) -> bool:
        """Check whether a connection has at least one recorded drone.

        Args:
            zone1: Name of the first endpoint zone.
            zone2: Name of the second endpoint zone.

        Returns:
            True if the stored connection occupancy is greater than zero.
        """
        return self.connection_occupancy(zone1, zone2) > 0

    def refresh(self, drones: Iterable[Drone]) -> None:
        """Replace counts using current drone positions.

        Args:
            drones: Drone states whose current positions or intents are
                inspected.
        """
        zones: dict[str, int] = {}
        connections: dict[tuple[str, str], int] = {}

        for drone in drones:
            if drone.zone is not None:
                name = drone.zone.name
                zones[name] = zones.get(name, 0) + 1

            if drone.connection is not None:
                link = drone.connection

                key = (
                    min(link.zone_name1, link.zone_name2),
                    max(link.zone_name1, link.zone_name2),
                )

                connections[key] = connections.get(key, 0) + 1

        self.zones = zones
        self.connections = connections
