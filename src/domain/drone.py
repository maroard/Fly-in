"""Track drone positions, restricted transits and delivery state."""

from src.domain.connection import Connection
from src.domain.zone import Zone


class Drone:
    """Track one drone on a zone, in transit or delivered.

    Attributes:
        id: Unique identifier assigned within the fleet.
        zone: Occupied zone, or None during transit.
        connection: Occupied connection, or None outside transit.
        target_zone: Transit destination, or None outside transit.
        delivered: Whether the drone has reached the end hub.
    """

    def __init__(self, drone_id: int, start_zone: Zone) -> None:
        """Place a new undelivered drone on its starting zone.

        Args:
            drone_id: Unique drone identifier.
            start_zone: Zone where the drone is initially placed.
        """
        self.id = drone_id

        self.zone: Zone | None = start_zone
        self.connection: Connection | None = None
        self.target_zone: Zone | None = None

        self.delivered: bool = False

    def move_to(self, destination: Zone) -> None:
        """Move directly to a zone and clear any transit state.

        Args:
            destination: Zone the drone should occupy after this movement.
        """
        self.zone = destination
        self.connection = None
        self.target_zone = None

    def start_transit(
        self,
        connection: Connection,
        target_zone: Zone,
    ) -> None:
        """Start a connection transit toward a restricted zone.

        Args:
            connection: Undirected connection used for transit or conflict
                checks.
            target_zone: Zone to occupy when the connection transit
                completes.

        Raises:
            RuntimeError: If the drone is already on a connection.
        """
        if self.connection is not None:
            raise RuntimeError(
                f"Drone {self.id} cannot start transiting "
                "because it is already in transit."
            )

        self.zone = None
        self.connection = connection
        self.target_zone = target_zone

    def arrive(self) -> None:
        """Complete the current transit and occupy its target zone.

        Raises:
            RuntimeError: If no transit target is stored.
        """
        if self.target_zone is None:
            raise RuntimeError(
                f"Drone {self.id} cannot arrive because it is not in transit."
            )

        self.zone = self.target_zone
        self.connection = None
        self.target_zone = None

    def deliver(self) -> None:
        """Mark the drone as delivered without clearing its final zone."""
        self.delivered = True
