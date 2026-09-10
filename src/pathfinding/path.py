from dataclasses import dataclass


@dataclass(frozen=True)
class Path:
    zones: tuple[str, ...]
