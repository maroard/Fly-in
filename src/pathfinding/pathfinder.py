import heapq
from math import inf

from src.domain import Connection, Graph, Zone
from src.pathfinding.path import Path


class PathFinder:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def find_shortest_path(
        self,
        start_zone: Zone | None = None,
        end_zone: Zone | None = None,
        excluded_zones: list[Zone] | None = None,
        excluded_connections: list[Connection] | None = None,
    ) -> Path | None:
        start = (
            start_zone
            if start_zone is not None
            else self.graph.start_hub
        )
        end = (
            end_zone
            if end_zone is not None
            else self.graph.end_hub
        )

        excluded_zones = (
            excluded_zones
            if excluded_zones is not None
            else []
        )
        excluded_connections = (
            excluded_connections
            if excluded_connections is not None
            else []
        )

        if start in excluded_zones or end in excluded_zones:
            return None

        distances: dict[str, float] = {
            zone_name: inf
            for zone_name in self.graph.zones
        }
        distances[start.name] = 0

        priority_counts: dict[str, int] = {
            zone_name: 0
            for zone_name in self.graph.zones
        }

        previous: dict[str, str] = {}

        queue: list[tuple[float, int, str]] = [
            (0, 0, start.name)
        ]

        while queue:
            (
                current_distance,
                negative_priority_count,
                current_name,
            ) = heapq.heappop(queue)

            current_priority_count = -negative_priority_count

            if current_distance > distances[current_name]:
                continue

            if (
                current_distance == distances[current_name]
                and current_priority_count
                < priority_counts[current_name]
            ):
                continue

            if current_name == end.name:
                break

            current_zone = self.graph.zones[current_name]

            for neighbor_name, connection in (
                self.graph.get_adjacencies(current_zone)
            ):
                neighbor = self.graph.zones[neighbor_name]

                if neighbor in excluded_zones:
                    continue

                if connection in excluded_connections:
                    continue

                if neighbor.metadata.zone_type == "blocked":
                    continue

                new_distance = (
                    current_distance
                    + self._get_zone_cost(neighbor)
                )

                new_priority_count = current_priority_count

                if neighbor.metadata.zone_type == "priority":
                    new_priority_count += 1

                is_shorter = (
                    new_distance < distances[neighbor_name]
                )

                has_more_priority = (
                    new_distance == distances[neighbor_name]
                    and new_priority_count
                    > priority_counts[neighbor_name]
                )

                if is_shorter or has_more_priority:
                    distances[neighbor_name] = new_distance
                    priority_counts[neighbor_name] = (
                        new_priority_count
                    )
                    previous[neighbor_name] = current_name

                    heapq.heappush(
                        queue,
                        (
                            new_distance,
                            -new_priority_count,
                            neighbor_name,
                        ),
                    )

        if distances[end.name] == inf:
            return None

        return self._build_path(
            previous=previous,
            start_name=start.name,
            end_name=end.name,
        )

    def _get_zone_cost(self, zone: Zone) -> int:
        if zone.metadata.zone_type == "restricted":
            return 2

        return 1

    def _build_path(
        self,
        previous: dict[str, str],
        start_name: str,
        end_name: str,
    ) -> Path:
        current_name = end_name
        zones: list[str] = [current_name]

        while current_name != start_name:
            current_name = previous[current_name]
            zones.append(current_name)

        zones.reverse()

        return Path(zones=tuple(zones))
