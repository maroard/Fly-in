from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, PositiveInt, field_validator


ZoneType = Literal["normal", "blocked", "restricted", "priority"]


class ZoneMetadata(BaseModel):
    zone_type: ZoneType = "normal"
    color: str | None = None
    max_drones: PositiveInt = 1

    @field_validator("color")
    @classmethod
    def validate_color(cls, color: str | None) -> str | None:
        if color is None:
            return color

        if not color or any(char.isspace() for char in color):
            raise ValueError(
                "color metadata must be a valid "
                "single-word string.\n"
                f"Got \"{color}\""
            )

        return color


class Zone(BaseModel):
    name: str
    x: int
    y: int
    metadata: ZoneMetadata = ZoneMetadata()

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        for char in name:
            if char == '-' or char == ' ':
                raise ValueError(
                    "A zone name can use any valid characters "
                    "except dashes and spaces.\n"
                    f"Got: {name}"
                )

        return name
