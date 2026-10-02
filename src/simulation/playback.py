"""Present calculated turns without changing the simulation rules."""

from dataclasses import dataclass
from threading import Lock
from typing import Literal

from src.domain.graph import Graph
from src.simulation.turn import Movement, Turn


@dataclass(frozen=True)
class Location:
    """Describe a drone zone or a directed position on a connection.

    Attributes:
        zone: Zone name, or None when occupying a connection.
        connection: Connection name, or None when occupying a zone.
        source: Transit source zone name for a connection position.
        target: Transit target zone name for a connection position.
    """

    zone: str | None = None
    connection: str | None = None
    source: str | None = None
    target: str | None = None


@dataclass(frozen=True)
class VisualDrone:
    """Describe an immutable visible movement and its progression.

    Attributes:
        start: Logical location from which the visible motion begins.
        end: Logical location reached at full progression.
        progress: Fraction of the motion completed, between zero and one.
    """

    start: Location
    end: Location
    progress: float


@dataclass(frozen=True)
class PlaybackSnapshot:
    """Expose a copied view of playback positions and progress.

    Attributes:
        positions: Fresh mapping of drone identifiers to visual positions.
        selected_drone_id: Highlighted drone identifier, or None.
        turn_index: Zero-based live playback turn index.
        completed_movements: Number of movements completed in live
            playback.
        finished: Whether the complete playback has finished.
    """

    positions: dict[int, VisualDrone]
    selected_drone_id: int | None
    turn_index: int
    completed_movements: int
    finished: bool


class Playback:
    """Track the visible part of an already calculated simulation.

    Attributes:
        graph: Graph used to resolve recorded movement destinations.
        turns: Complete simulation turns in their original order.
        mode: Automatic or movement-by-movement playback mode.
        seconds_per_movement: Positive duration of each visible animation.
        turn_index: Zero-based index of the live turn.
        completed_movements: Number of movements applied to live locations.
        finished: Whether every recorded movement has completed.
        last_elapsed: Most recent cumulative animation time.
        selected_drone_id: Highlighted drone identifier, or None.
    """

    def __init__(
        self,
        graph: Graph,
        turns: list[Turn],
        mode: Literal["one_shot", "step_by_step"],
        seconds_per_movement: float,
    ) -> None:
        """Initialize playback with every drone on the starting hub.

        Args:
            graph: Graph containing the fleet size, zones and connections.
            turns: Already calculated turns, kept in their simulation
                order.
            mode: Playback mode: one_shot or step_by_step.
            seconds_per_movement: Strictly positive animation duration in
                seconds.
        """
        self.graph = graph
        self.turns = turns

        self.mode = mode
        self.seconds_per_movement = seconds_per_movement

        self.turn_index = 0
        self.completed_movements = 0
        self.finished = not turns
        self.last_elapsed = 0.0

        self.selected_drone_id: int | None = None
        self._locations = self._initial_locations()
        self._replay_locations: dict[int, Location] | None = None

        self._active: list[tuple[int, Location, Location]] = []
        self._active_since = 0.0
        self._next_movement = 0
        self._started = False

        self._lock = Lock()

    def select_drone(self, drone_id: int | None) -> None:
        """Set the highlighted drone or clear its selection.

        Args:
            drone_id: Identifier to highlight, or None to clear the
                selection.
        """
        with self._lock:
            self.selected_drone_id = drone_id

    def clear_replay(self) -> None:
        """Restore live positions and clear the highlighted drone."""
        with self._lock:
            self._replay_locations = None
            self.selected_drone_id = None

    def select_movement(self, turn_index: int, movement_index: int) -> None:
        """Show the state just after one completed movement.

        Reconstruct positions through the selected row in movement order
        without changing live progress counters.

        Args:
            turn_index: Zero-based index of the historical turn to inspect.
            movement_index: Zero-based index of the movement within that
                turn.

        Raises:
            ValueError: If playback has not finished.
            IndexError: If the requested turn or movement index is out of
                bounds.
        """
        with self._lock:
            if not self.finished:
                raise ValueError("Replay needs a finished movement")

            movement = self.turns[turn_index].movements[movement_index]
            locations = self._initial_locations()

            for current_turn_index in range(turn_index + 1):
                turn = self.turns[current_turn_index]
                movement_count = len(turn.movements)

                if current_turn_index == turn_index:
                    movement_count = movement_index + 1

                for prior in turn.movements[:movement_count]:
                    drone_id, _, end = self._motion(prior, locations)
                    locations[drone_id] = end

            self._replay_locations = locations
            self.selected_drone_id = movement.drone_id

    def start_next_movement(self) -> bool:
        """Start one waiting movement in step mode; ignore repeated presses.

        Returns:
            True if a step started, False if unavailable, active or
            finished.
        """
        with self._lock:
            if (
                self.mode != "step_by_step"
                or self.finished
                or self._active
            ):
                return False

            movement = self.turns[self.turn_index].movements[
                self._next_movement
            ]

            self._active = [self._motion(movement)]
            self._active_since = self.last_elapsed
            self._replay_locations = None

            return True

    @property
    def current_movement_index(self) -> int:
        """Return the active or waiting movement index.

        Returns:
            Active or waiting row index, capped at the last row when
            finished.
        """
        with self._lock:
            return min(
                self._next_movement,
                len(self.turns[self.turn_index].movements) - 1,
            )

    def previous_movement(self) -> bool:
        """Cancel an active step, or undo the last completed step.

        Returns:
            True if an animation was canceled or a completed movement
            undone.
        """
        with self._lock:
            if self.mode != "step_by_step" or not self.turns:
                return False

            if not self._active and self.completed_movements == 0:
                return False

            if not self._active:
                self.completed_movements -= 1

            self._active = []
            self._replay_locations = None
            self.finished = False
            self.selected_drone_id = None

            locations = self._initial_locations()
            remaining = self.completed_movements

            for turn_index, turn in enumerate(self.turns):
                for movement_index, movement in enumerate(turn.movements):
                    if remaining == 0:
                        self.turn_index = turn_index
                        self._next_movement = movement_index
                        self._locations = locations

                        return True

                    drone_id, _, end = self._motion(movement, locations)
                    locations[drone_id] = end
                    remaining -= 1

            return False

    def advance(self, elapsed: float) -> bool:
        """Advance visible motion; report a page change.

        Args:
            elapsed: Cumulative elapsed seconds from the animation loop.

        Returns:
            True if the turn index changed; finishing alone does not imply
            True.
        """
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
        """Copy the visible state for a renderer running on another thread.

        Returns:
            Copied visible positions, selection and playback counters.
        """
        with self._lock:
            locations = self._locations

            if self._replay_locations is not None:
                locations = self._replay_locations

            positions = {
                drone_id: VisualDrone(location, location, 1.0)
                for drone_id, location in locations.items()
            }

            if self._active and self._replay_locations is None:
                progress = min(
                    1.0,
                    max(
                        0.0,
                        (self.last_elapsed - self._active_since)
                        / self.seconds_per_movement,
                    ),
                )

                for drone_id, start, end in self._active:
                    positions[drone_id] = VisualDrone(
                        start,
                        end,
                        progress
                    )

            return PlaybackSnapshot(
                positions,
                self.selected_drone_id,
                self.turn_index,
                self.completed_movements,
                self.finished,
            )

    def _start_turn(self, elapsed: float) -> None:
        """Start all movements of the current turn together.

        Args:
            elapsed: Cumulative time when the current turn animation
                begins.
        """
        self._active = [
            self._motion(movement)
            for movement in self.turns[self.turn_index].movements
        ]

        self._active_since = elapsed

    def _initial_locations(self) -> dict[int, Location]:
        """Place every numbered drone at the starting hub.

        Returns:
            Drone identifiers from one to fleet size mapped to the start
            hub.
        """
        return {
            drone_id: Location(zone=self.graph.start_hub.name)
            for drone_id in range(1, self.graph.nb_drones + 1)
        }

    def _motion(
        self,
        movement: Movement,
        locations: dict[int, Location] | None = None,
    ) -> tuple[int, Location, Location]:
        """Resolve a drone movement into its start and destination.

        Args:
            movement: Recorded drone identifier and destination.
            locations: Source positions to consult; None uses live playback
                positions.

        Returns:
            Drone identifier, starting location and resolved destination.

        Raises:
            ValueError: If a connection movement starts outside a zone.
        """
        if locations is None:
            locations = self._locations

        start = locations[movement.drone_id]

        if movement.destination in self.graph.zones:
            end = Location(zone=movement.destination)
        else:
            if start.zone is None:
                raise ValueError(
                    "A connection movement must start from a zone"
                )

            connection = next(
                connection
                for connection in self.graph.connections
                if f"{connection.zone_name1}-{connection.zone_name2}"
                == movement.destination
            )

            target = (
                connection.zone_name2
                if connection.zone_name1 == start.zone
                else connection.zone_name1
            )

            end = Location(
                connection=movement.destination,
                source=start.zone,
                target=target,
            )

        return movement.drone_id, start, end
