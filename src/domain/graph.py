"""Build the graph and adjacency lists from a parsed map."""

from src.parsing.map_config import MapConfig
from src.domain.connection import Connection
from src.domain.zone import Zone


class Graph:
    """Store map resources and build their undirected adjacency lists.

    Attributes:
        nb_drones: Fleet size defined by the map.
        start_hub: Zone where all drones begin.
        end_hub: Delivery zone shared by arriving drones.
        zones: Zones indexed by their unique names.
        connections: Undirected map connections.
        adjacencies: Neighbor names and connections indexed by zone name.
    """

    def __init__(self, map_config: MapConfig):
        """Load map resources and index each connection in both directions.

        Args:
            map_config: Parsed map resources used to construct the graph.
        """
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
        """Return the neighbors and connections of a zone.

        Args:
            zone: Zone to inspect.

        Returns:
            Stored neighbor names and their corresponding connections.
        """
        return self.adjacencies[zone.name]

    def get_connection(
        self,
        zone1: Zone,
        zone2: Zone,
    ) -> Connection:
        """Find the undirected connection joining two zones.

        Args:
            zone1: First endpoint zone.
            zone2: Second endpoint zone.

        Returns:
            Connection joining the zones, regardless of endpoint order.

        Raises:
            ValueError: If no connection joins the two zones.
        """
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
