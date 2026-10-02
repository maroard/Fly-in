"""Define zones and validate their movement and display metadata."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, PositiveInt, field_validator


ZoneType = Literal["normal", "blocked", "restricted", "priority"]


class ZoneMetadata(BaseModel):
    """Validate zone movement rules, display color and capacity.

    Attributes:
        zone_type: Movement category: normal, blocked, restricted or
            priority.
        color: Optional single-word terminal color, including rainbow.
        max_drones: Positive maximum occupancy for an ordinary zone.
    """

    zone_type: ZoneType = "normal"
    color: str | None = None
    max_drones: PositiveInt = 1

    @field_validator("color")
    @classmethod
    def validate_color(cls, color: str | None) -> str | None:
        """Accept an optional color containing a single nonempty word.

        Args:
            color: Optional color string to validate.

        Returns:
            The unchanged valid color, or None when no color was provided.

        Raises:
            ValueError: If the color is empty or contains whitespace.
        """
        if color is None:
            return color

        if not color or any(char.isspace() for char in color):
            raise ValueError(
                "color metadata must be a valid "
                "single-word string.\n"
                f'Got "{color}"'
            )

        return color


class Zone(BaseModel):
    """Describe a named zone with graph coordinates and movement metadata.

    Attributes:
        name: Unique zone name without dashes or spaces.
        x: Integer horizontal graph coordinate.
        y: Integer vertical graph coordinate.
        metadata: Zone movement, color and capacity settings.
    """

    name: str
    x: int
    y: int
    metadata: ZoneMetadata = ZoneMetadata()

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        """Reject zone names containing dashes or spaces.

        Args:
            name: Zone name to validate.

        Returns:
            The unchanged valid zone name.

        Raises:
            ValueError: If the name contains a dash or a space.
        """
        for char in name:
            if char == '-' or char == ' ':
                raise ValueError(
                    "A zone name can use any valid characters "
                    "except dashes and spaces.\n"
                    f'Got: "{name}"'
                )

        return name
