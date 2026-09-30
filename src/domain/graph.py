from src.parsing.map_config import MapConfig
from src.domain.connection import Connection
from src.domain.zone import Zone


class Graph:
    def __init__(self, map_config: MapConfig):
        self.nb_drones: int = map_config.nb_drones
        self.start_hub: Zone = map_config.start_hub
        self.end_hub: Zone = map_config.end_hub
        self.zones: dict[str, Zone] = map_config.zones
        self.connections: list[Connection] = map_config.connections

        self.adjacencies: dict[str, list[tuple[str, Connection]]] = {}
        for zone in self.zones.values():
            self.adjacencies[zone.name] = []
        for connection in self.connections:
            self.adjacencies[connection.zone_name1].append(
                (connection.zone_name2, connection)
            )
            self.adjacencies[connection.zone_name2].append(
                (connection.zone_name1, connection)
            )

    def get_adjacencies(
        self,
        zone: Zone
    ) -> list[tuple[str, Connection]]:
        return self.adjacencies[zone.name]

    def get_connection(self, zone1: Zone, zone2: Zone) -> Connection:
        for connection in self.connections:
            if (
                connection.zone_name1 == zone1.name
                and connection.zone_name2 == zone2.name
            ) or (
                connection.zone_name1 == zone2.name
                and connection.zone_name2 == zone1.name
            ):
                return connection

        raise ValueError(
            f"No connection between '{zone1.name}' and '{zone2.name}'."
        )
