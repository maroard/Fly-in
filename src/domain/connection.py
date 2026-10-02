"""Define undirected connections and their capacity metadata."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, PositiveInt


class ConnectionMetadata(BaseModel):
    """Validate the capacity allowed on an undirected connection.

    Attributes:
        max_link_capacity: Positive maximum number of drones crossing per
            turn.
    """

    max_link_capacity: PositiveInt = 1


@dataclass
class Connection:
    """Describe an undirected connection between two named zones.

    Attributes:
        zone_name1: Name of one endpoint zone.
        zone_name2: Name of the other endpoint zone.
        metadata: Connection capacity constraints.
    """

    zone_name1: str
    zone_name2: str
    metadata: ConnectionMetadata
