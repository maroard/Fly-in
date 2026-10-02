"""Collect validated map resources before graph construction."""

from dataclasses import dataclass

from src.domain.connection import Connection
from src.domain.zone import Zone


@dataclass
class MapConfig:
    """Collect the parsed fleet, hubs, zones and connections of a map.

    Attributes:
        nb_drones: Number of drones to simulate.
        start_hub: Unique starting zone.
        end_hub: Unique delivery zone.
        zones: All parsed zones indexed by name.
        connections: All parsed undirected connections.
    """

    nb_drones: int
    start_hub: Zone
    end_hub: Zone
    zones: dict[str, Zone]
    connections: list[Connection]
