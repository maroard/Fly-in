from collections.abc import Iterable
from dataclasses import dataclass, field

from src.domain.drone import Drone


@dataclass
class Occupancy:
    """Share a snapshot of drone positions without simulation dependencies.

    Connections are undirected. Delivered drones still count while they retain
    a zone. Refresh after position changes; target zones are not reservations.
    """

    zones: dict[str, int] = field(default_factory=dict)
    connections: dict[tuple[str, str], int] = field(default_factory=dict)

    def zone_occupancy(self, zone_name: str) -> int:
        return self.zones.get(zone_name, 0)

    def connection_occupancy(self, zone1: str, zone2: str) -> int:
        key = (min(zone1, zone2), max(zone1, zone2))
        return self.connections.get(key, 0)

    def is_zone_occupied(self, zone_name: str) -> bool:
        return self.zone_occupancy(zone_name) > 0

    def is_connection_occupied(self, zone1: str, zone2: str) -> bool:
        return self.connection_occupancy(zone1, zone2) > 0

    def refresh(self, drones: Iterable[Drone]) -> None:
        """Replace counts using current drone positions."""
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
