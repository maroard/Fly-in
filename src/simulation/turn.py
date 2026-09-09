from dataclasses import dataclass, field


@dataclass(frozen=True)
class Movement:
    drone_id: int
    destination: str


@dataclass
class Turn:
    number: int
    movements: list[Movement] = field(default_factory=list)
