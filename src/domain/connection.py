from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, PositiveInt


class ConnectionMetadata(BaseModel):
    max_link_capacity: PositiveInt = 1


@dataclass
class Connection:
    zone_name1: str
    zone_name2: str
    metadata: ConnectionMetadata
