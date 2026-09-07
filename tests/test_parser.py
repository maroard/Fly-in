from pathlib import Path

import pytest

from src.parsing.parser import Parser


BASE_MAP = """nb_drones: 2
start_hub: s 0 0
end_hub: e 2 0
hub: a 1 0
connection: s-a
connection: a-e
"""


def parse_map(tmp_path: Path, content: str) -> Parser:
    path = tmp_path / "map.txt"
    path.write_text(content, encoding="utf-8")
    return Parser(path)


@pytest.mark.parametrize("metadata", [
    "[color=red]]",
    "[color=[red]",
    "[[color=red]]",
    "[color=red] [zone=normal]",
    "[color=red",
])
@pytest.mark.parametrize("zone", ["s 0 0", "a 1 0"])
def test_rejects_malformed_metadata(
    tmp_path: Path, metadata: str, zone: str,
) -> None:
    content = BASE_MAP.replace(zone, f"{zone} {metadata}")
    line_number = 2 if zone.startswith("s") else 4
    message = f"Parsing error at line {line_number}"
    with pytest.raises(ValueError, match=message):
        parse_map(tmp_path, content).process()


def test_valid_metadata_is_converted(tmp_path: Path) -> None:
    content = BASE_MAP.replace(
        "a 1 0", "a -1 0 [max_drones=3 color=blue zone=priority]"
    ).replace("s-a", "s-a [max_link_capacity=2]")
    config = parse_map(tmp_path, content).process()
    zone = config.zones["a"]
    assert zone.x == -1
    assert zone.metadata.max_drones == 3
    assert zone.metadata.color == "blue"
    assert zone.metadata.zone_type == "priority"
    assert config.connections[0].metadata.max_link_capacity == 2


@pytest.mark.parametrize("capacity", ["0", "-1", "1.5", "abc"])
@pytest.mark.parametrize("field", ["max_drones", "max_link_capacity"])
def test_rejects_invalid_capacity(
    tmp_path: Path, capacity: str, field: str,
) -> None:
    target = "a 1 0" if field == "max_drones" else "s-a"
    content = BASE_MAP.replace(target, f"{target} [{field}={capacity}]")
    message = f"{field} must be a positive integer"
    with pytest.raises(ValueError, match=message):
        parse_map(tmp_path, content).process()


@pytest.mark.parametrize("capacity", ["0", "-1", "1.5", "abc"])
def test_endpoint_capacity_is_ignored(tmp_path: Path, capacity: str) -> None:
    content = BASE_MAP.replace(
        "s 0 0", f"s 0 0 [max_drones={capacity}]"
    ).replace("e 2 0", f"e 2 0 [max_drones={capacity}]")
    config = parse_map(tmp_path, content).process()
    assert config.start_hub.name == "s"
    assert config.end_hub.name == "e"


@pytest.mark.parametrize("map_path", sorted(
    path for path in Path("maps").glob("*/*.txt")
    if path.parent.name != "custom"
))
def test_provided_maps(map_path: Path) -> None:
    config = Parser(map_path).process()
    assert config.nb_drones > 0
    assert config.start_hub.name in config.zones
    assert config.end_hub.name in config.zones
