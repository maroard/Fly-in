"""Present calculated turns without changing the simulation rules."""

from dataclasses import dataclass
from threading import Lock
from typing import Literal

from src.domain.graph import Graph
from src.simulation.turn import Movement, Turn


@dataclass(frozen=True)
class Location:
    zone: str | None = None
    connection: str | None = None
    source: str | None = None
    target: str | None = None


@dataclass(frozen=True)
class VisualDrone:
    start: Location
    end: Location
    progress: float


@dataclass(frozen=True)
class PlaybackSnapshot:
    positions: dict[int, VisualDrone]
    selected_drone_id: int | None
    turn_index: int
    completed_movements: int
    finished: bool


class Playback:
    """Track the visible part of an already calculated simulation."""

    def __init__(
        self,
        graph: Graph,
        turns: list[Turn],
        mode: Literal["one_shot", "step_by_step"],
        seconds_per_movement: float,
    ) -> None:
        self.graph = graph
        self.turns = turns
        self.mode = mode
        self.seconds_per_movement = seconds_per_movement
        self.turn_index = 0
        self.completed_movements = 0
        self.finished = not turns
        self.last_elapsed = 0.0
        self.selected_drone_id: int | None = None
        self._locations = {
            drone_id: Location(zone=graph.start_hub.name)
            for drone_id in range(1, graph.nb_drones + 1)
        }
        self._active: list[tuple[int, Location, Location]] = []
        self._active_since = 0.0
        self._next_movement = 0
        self._started = False
        self._lock = Lock()

    def select_drone(self, drone_id: int | None) -> None:
        with self._lock:
            self.selected_drone_id = drone_id

    def start_next_movement(self) -> bool:
        """Start one waiting movement in step mode; ignore repeated presses."""
        with self._lock:
            if self.mode != "step_by_step" or self.finished or self._active:
                return False
            movement = self.turns[self.turn_index].movements[
                self._next_movement
            ]
            self._active = [self._motion(movement)]
            self._active_since = self.last_elapsed
            return True

    def advance(self, elapsed: float) -> bool:
        """Advance visible motion; report a page change."""
        with self._lock:
            self.last_elapsed = elapsed
            if self.finished:
                return False
            if self.mode == "one_shot" and not self._started:
                self._started = True
                self._start_turn(elapsed)

            page_changed = False
            while (
                self._active
                and elapsed >= self._active_since + self.seconds_per_movement
            ):
                next_start = self._active_since + self.seconds_per_movement
                for drone_id, _, end in self._active:
                    self._locations[drone_id] = end
                self.completed_movements += len(self._active)
                self._next_movement += len(self._active)
                self._active = []
                if self._next_movement == len(
                    self.turns[self.turn_index].movements
                ):
                    if self.turn_index + 1 == len(self.turns):
                        self.finished = True
                    else:
                        self.turn_index += 1
                        self._next_movement = 0
                        page_changed = True
                        if self.mode == "one_shot":
                            self._start_turn(next_start)
            return page_changed

    def snapshot(self) -> PlaybackSnapshot:
        """Copy the visible state for a renderer running on another thread."""
        with self._lock:
            positions = {
                drone_id: VisualDrone(location, location, 1.0)
                for drone_id, location in self._locations.items()
            }
            if self._active:
                progress = min(1.0, max(
                    0.0,
                    (self.last_elapsed - self._active_since)
                    / self.seconds_per_movement,
                ))
                for drone_id, start, end in self._active:
                    positions[drone_id] = VisualDrone(start, end, progress)
            return PlaybackSnapshot(
                positions, self.selected_drone_id, self.turn_index,
                self.completed_movements, self.finished,
            )

    def _start_turn(self, elapsed: float) -> None:
        self._active = [
            self._motion(movement)
            for movement in self.turns[self.turn_index].movements
        ]
        self._active_since = elapsed

    def _motion(self, movement: Movement) -> tuple[int, Location, Location]:
        start = self._locations[movement.drone_id]
        if movement.destination in self.graph.zones:
            end = Location(zone=movement.destination)
        else:
            if start.zone is None:
                raise ValueError(
                    "A connection movement must start from a zone"
                )
            connection = next(
                connection for connection in self.graph.connections
                if f"{connection.zone_name1}-{connection.zone_name2}"
                == movement.destination
            )
            target = (
                connection.zone_name2
                if connection.zone_name1 == start.zone
                else connection.zone_name1
            )
            end = Location(
                connection=movement.destination, source=start.zone,
                target=target,
            )
        return movement.drone_id, start, end
