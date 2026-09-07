from dataclasses import dataclass

from src.domain.connection import Connection
from src.domain.zone import Zone


@dataclass
class MapConfig:
    nb_drones: int
    start_hub: Zone
    end_hub: Zone
    zones: dict[str, Zone]
    connections: list[Connection]
    note: str = ""
