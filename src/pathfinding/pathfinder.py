from math import inf
import heapq

from src.domain import Graph
from src.pathfinding.path import Path


class PathFinder:
    def __init__(self, graph: Graph):
        self.graph = graph

    def find_shortest_path(self) -> Path | None:
        distances: dict[str, float] = {
            zone_name: inf
            for zone_name in self.graph.zones
        }
        distances[self.graph.start_hub.name] = 0
        previous: dict[str, str] = {}
        queue: list[tuple[float, str]] = [(0, self.graph.start_hub.name)]

