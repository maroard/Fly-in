import heapq
from math import inf

from src.domain import Graph, Zone
from src.pathfinding.path import Path


class PathFinder:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def find_shortest_path(self) -> Path | None:
        start_name = self.graph.start_hub.name
        end_name = self.graph.end_hub.name

        distances: dict[str, float] = {
            zone_name: inf
            for zone_name in self.graph.zones
        }
        distances[start_name] = 0

        previous: dict[str, str] = {}

        queue: list[tuple[float, str]] = [
            (0, start_name)
        ]

        while queue:
            current_distance, current_name = heapq.heappop(queue)

            if current_distance > distances[current_name]:
                continue

            if current_name == end_name:
                break

            current_zone = self.graph.zones[current_name]

            for neighbor_name, _ in self.graph.get_adjacencies(current_zone):
                neighbor = self.graph.zones[neighbor_name]

                if neighbor.metadata.zone_type == "blocked":
                    continue

                new_distance = (
                    current_distance
                    + self._get_zone_cost(neighbor)
                )

                if new_distance < distances[neighbor_name]:
                    distances[neighbor_name] = new_distance
                    previous[neighbor_name] = current_name

                    heapq.heappush(
                        queue,
                        (new_distance, neighbor_name)
                    )

        if distances[end_name] == inf:
            return None

        return self._build_path(previous)

    def _get_zone_cost(self, zone: Zone) -> int:
        if zone.metadata.zone_type == "restricted":
            return 2

        return 1

    def _build_path(self, previous: dict[str, str]) -> Path:
        current_name = self.graph.end_hub.name
        zones: list[str] = [current_name]

        while current_name != self.graph.start_hub.name:
            current_name = previous[current_name]
            zones.append(current_name)

        zones.reverse()

        return Path(zones=tuple(zones))
