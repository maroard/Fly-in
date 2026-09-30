from dataclasses import dataclass


@dataclass(frozen=True)
class Path:
    zones: tuple[str, ...]

    def get_next_zone_name(self, current_zone_name: str) -> str | None:
        zone_index: int = self.zones.index(current_zone_name)

        if zone_index == len(self.zones) - 1:
            return None

        return self.zones[zone_index + 1]
