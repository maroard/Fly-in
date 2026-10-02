"""Represent ordered zone paths assigned to drones."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Path:
    """Store an immutable ordered sequence of zone names.

    Attributes:
        zones: Zone names in traversal order, including both endpoints.
    """

    zones: tuple[str, ...]

    def get_next_zone_name(self, current_zone_name: str) -> str | None:
        """Find the zone following a current zone along the path.

        Args:
            current_zone_name: Name of the drone current zone on the path.

        Returns:
            Next zone name, or None if the current zone is the path end.

        Raises:
            ValueError: If the current zone name is absent from this path.
        """
        zone_index: int = self.zones.index(current_zone_name)

        if zone_index == len(self.zones) - 1:
            return None

        return self.zones[zone_index + 1]
