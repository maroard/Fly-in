from src.domain.connection import Connection
from src.domain.zone import Zone


class Drone:
    def __init__(self, drone_id: int, start_zone: Zone) -> None:
        self.id = drone_id
        self.zone: Zone | None = start_zone
        self.connection: Connection | None = None
        self.target_zone: Zone | None = None
        self.delivered: bool = False

    def move_to(self, destination: Zone) -> None:
        self.zone = destination
        self.connection = None
        self.target_zone = None

    def start_transit(self, connection: Connection, target_zone: Zone) -> None:
        if self.connection is not None:
            raise RuntimeError(
                f"Drone {self.id} cannot start transiting "
                "because it is already in transit."
            )

        self.zone = None
        self.connection = connection
        self.target_zone = target_zone

    def arrive(self) -> None:
        if self.target_zone is None:
            raise RuntimeError(
                f"Drone {self.id} cannot arrive because it is not in transit."
            )

        self.zone = self.target_zone
        self.connection = None
        self.target_zone = None

    def deliver(self) -> None:
        self.delivered = True
