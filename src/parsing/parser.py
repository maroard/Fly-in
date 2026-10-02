"""Parse Fly-in map definitions and report contextual input errors."""

from pathlib import Path
from typing import NoReturn

from pydantic import ValidationError

from src.domain.connection import Connection, ConnectionMetadata
from src.domain.zone import Zone, ZoneMetadata
from src.parsing.map_config import MapConfig


class Parser:
    """Read and validate a Fly-in map with contextual parsing errors.

    Attributes:
        content: Input file lines without their newline terminators.
    """

    def __init__(self, map_path: Path) -> None:
        """Read the map file as UTF-8 lines.

        Args:
            map_path: Path to the map file to read.

        Raises:
            ValueError: If no map path is supplied.
            OSError: If the map file cannot be read.
            UnicodeDecodeError: If the file content is not valid UTF-8.
        """
        if not map_path:
            raise ValueError(
                "map_path cannot be nothing"
            )

        with map_path.open(mode="r", encoding="utf-8") as file:
            self.content: list[str] = file.read().splitlines()

    def process(self) -> MapConfig:
        """Parse all definitions and require one fleet, start hub and end hub.

        Returns:
            Validated map configuration ready to construct a graph.

        Raises:
            ValueError: If map syntax, values or required definitions are
                invalid.
        """
        nb_drones: int | None = None
        start_hub: Zone | None = None
        end_hub: Zone | None = None

        zones: dict[str, Zone] = {}
        connections: list[Connection] = []

        seen_connections: set[tuple[str, str]] = set()
        first_data_line_seen = False

        for line_number, raw_line in enumerate(self.content, start=1):
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            key, value = self._split_line(
                line,
                line_number,
            )

            if not first_data_line_seen:
                if key != "nb_drones":
                    self._raise_parsing_error(
                        line_number,
                        raw_line,
                        "the first data line must define nb_drones",
                    )

                nb_drones = self._get_nb_drones(
                    value,
                    line_number,
                    raw_line,
                )
                first_data_line_seen = True

                continue

            if key == "nb_drones":
                self._raise_parsing_error(
                    line_number,
                    raw_line,
                    "nb_drones must only be defined once",
                )

            if key in {"start_hub", "end_hub", "hub"}:
                zone = self._get_zone(
                    value,
                    line_number,
                    raw_line,
                    ignore_capacity=key in {"start_hub", "end_hub"},
                )

                if zone.name in zones:
                    self._raise_parsing_error(
                        line_number,
                        raw_line,
                        f'zone name "{zone.name}" is already defined',
                    )

                if key == "start_hub":
                    if start_hub is not None:
                        self._raise_parsing_error(
                            line_number,
                            raw_line,
                            "start_hub must be defined exactly once",
                        )

                    start_hub = zone

                elif key == "end_hub":
                    if end_hub is not None:
                        self._raise_parsing_error(
                            line_number,
                            raw_line,
                            "end_hub must be defined exactly once",
                        )

                    end_hub = zone

                zones[zone.name] = zone

                continue

            if key == "connection":
                connection = self._get_connection(
                    value,
                    zones,
                    seen_connections,
                    line_number,
                    raw_line,
                )

                connections.append(connection)

                continue

            self._raise_parsing_error(
                line_number,
                raw_line,
                f'unknown key "{key}"',
            )

        eof_line = len(self.content) + 1

        if nb_drones is None:
            self._raise_parsing_error(
                eof_line,
                "",
                "missing nb_drones definition",
            )

        if start_hub is None:
            self._raise_parsing_error(
                eof_line,
                "",
                "missing start_hub definition",
            )

        if end_hub is None:
            self._raise_parsing_error(
                eof_line,
                "",
                "missing end_hub definition",
            )

        return MapConfig(
            nb_drones=nb_drones,
            start_hub=start_hub,
            end_hub=end_hub,
            zones=zones,
            connections=connections,
        )

    def _get_zone(
        self,
        raw_value: str,
        line_number: int,
        raw_line: str,
        ignore_capacity: bool = False,
    ) -> Zone:
        """Parse one zone and validate its coordinates and metadata.

        Args:
            raw_value: Unparsed value from a map definition.
            line_number: One-based input line number used in error
                messages.
            raw_line: Original input line included in parsing error
                messages.
            ignore_capacity: Whether to ignore max_drones for a start or
                end hub.

        Returns:
            Zone with parsed coordinates and validated metadata.

        Raises:
            ValueError: If the zone name, coordinates or metadata are
                invalid.
        """
        values = raw_value.split(maxsplit=3)

        if len(values) not in {3, 4}:
            self._raise_parsing_error(
                line_number,
                raw_line,
                "a zone must contain a name, x and y coordinates, "
                "and optional metadata",
            )

        name, raw_x, raw_y = values[:3]

        self._validate_zone_name(
            name,
            line_number,
            raw_line,
        )

        try:
            x = int(raw_x)
            y = int(raw_y)
        except ValueError:
            self._raise_parsing_error(
                line_number,
                raw_line,
                "zone coordinates must be valid integers",
            )

        metadata_values: dict[str, str] = {}

        if len(values) == 4:
            metadata_values = self._parse_metadata(
                values[3],
                {"zone", "color", "max_drones"},
                line_number,
                raw_line,
            )

        if ignore_capacity:
            metadata_values.pop("max_drones", None)
        elif "max_drones" in metadata_values:
            metadata_values["max_drones"] = str(
                self._parse_positive_integer(
                    metadata_values["max_drones"],
                    "max_drones",
                    line_number,
                    raw_line,
                )
            )

        if "zone" in metadata_values:
            metadata_values["zone_type"] = metadata_values.pop("zone")

        try:
            metadata = ZoneMetadata.model_validate(metadata_values)
        except ValidationError as error:
            self._raise_parsing_error(
                line_number,
                raw_line,
                self._format_validation_error(error),
            )

        return Zone(
            name=name,
            x=x,
            y=y,
            metadata=metadata,
        )

    def _get_connection(
        self,
        raw_value: str,
        zones: dict[str, Zone],
        seen_connections: set[tuple[str, str]],
        line_number: int,
        raw_line: str,
    ) -> Connection:
        """Parse a unique connection between already defined zones.

        Args:
            raw_value: Unparsed value from a map definition.
            zones: Zones already parsed, indexed by name.
            seen_connections: Canonical endpoint pairs, updated with the
                new connection.
            line_number: One-based input line number used in error
                messages.
            raw_line: Original input line included in parsing error
                messages.

        Returns:
            Connection with validated endpoints and metadata.

        Raises:
            ValueError: If endpoints, uniqueness or metadata are invalid.
        """
        values = raw_value.split(maxsplit=1)
        raw_connection = values[0]

        names = raw_connection.split("-")

        if len(names) != 2 or not all(names):
            self._raise_parsing_error(
                line_number,
                raw_line,
                "connection must use the format <zone1>-<zone2>",
            )

        zone_name1, zone_name2 = names

        for zone_name in (zone_name1, zone_name2):
            if zone_name not in zones:
                self._raise_parsing_error(
                    line_number,
                    raw_line,
                    f'zone "{zone_name}" must be defined before '
                    "the connection",
                )

        if zone_name1 <= zone_name2:
            connection_key = (zone_name1, zone_name2)
        else:
            connection_key = (zone_name2, zone_name1)

        if connection_key in seen_connections:
            self._raise_parsing_error(
                line_number,
                raw_line,
                "the same connection cannot appear more than once",
            )

        metadata_values: dict[str, str] = {}

        if len(values) == 2:
            metadata_values = self._parse_metadata(
                values[1],
                {"max_link_capacity"},
                line_number,
                raw_line,
            )

        if "max_link_capacity" in metadata_values:
            metadata_values["max_link_capacity"] = str(
                self._parse_positive_integer(
                    metadata_values["max_link_capacity"],
                    "max_link_capacity",
                    line_number,
                    raw_line,
                )
            )

        try:
            metadata = ConnectionMetadata.model_validate(metadata_values)
        except ValidationError as error:
            self._raise_parsing_error(
                line_number,
                raw_line,
                self._format_validation_error(error),
            )

        seen_connections.add(connection_key)

        return Connection(
            zone_name1=zone_name1,
            zone_name2=zone_name2,
            metadata=metadata,
        )

    @staticmethod
    def _parse_positive_integer(
        raw_value: str,
        field_name: str,
        line_number: int,
        raw_line: str,
    ) -> int:
        """Parse an integer strictly greater than zero.

        Args:
            raw_value: Unparsed value from a map definition.
            field_name: Name of the integer field reported in parsing
                errors.
            line_number: One-based input line number used in error
                messages.
            raw_line: Original input line included in parsing error
                messages.

        Returns:
            Parsed strictly positive integer.

        Raises:
            ValueError: If the value is not an integer greater than zero.
        """
        try:
            value = int(raw_value)
        except ValueError:
            Parser._raise_parsing_error(
                line_number,
                raw_line,
                f"{field_name} must be a positive integer",
            )

        if value <= 0:
            Parser._raise_parsing_error(
                line_number,
                raw_line,
                f"{field_name} must be a positive integer",
            )

        return value

    @staticmethod
    def _get_nb_drones(
        raw_value: str,
        line_number: int,
        raw_line: str,
    ) -> int:
        """Parse the strictly positive fleet size.

        Args:
            raw_value: Unparsed value from a map definition.
            line_number: One-based input line number used in error
                messages.
            raw_line: Original input line included in parsing error
                messages.

        Returns:
            Number of drones required by the map.

        Raises:
            ValueError: If the fleet size is not a positive integer.
        """
        return Parser._parse_positive_integer(
            raw_value,
            "nb_drones",
            line_number,
            raw_line,
        )

    @staticmethod
    def _split_line(
        line: str,
        line_number: int,
    ) -> tuple[str, str]:
        """Split a definition into its stripped key and value.

        Args:
            line: Input line to split or include in a parsing error.
            line_number: One-based input line number used in error
                messages.

        Returns:
            Stripped definition key and value.

        Raises:
            ValueError: If the separator, key or value is missing.
        """
        key, separator, value = line.partition(":")

        key = key.strip()
        value = value.strip()

        if not separator or not key or not value:
            Parser._raise_parsing_error(
                line_number,
                line,
                "key and value must be separated by ':'",
            )

        return key, value

    @staticmethod
    def _parse_metadata(
        raw_metadata: str,
        allowed_keys: set[str],
        line_number: int,
        raw_line: str,
    ) -> dict[str, str]:
        """Parse bracketed metadata and reject invalid or repeated keys.

        Args:
            raw_metadata: Bracketed metadata text from the map file.
            allowed_keys: Metadata keys permitted for this definition.
            line_number: One-based input line number used in error
                messages.
            raw_line: Original input line included in parsing error
                messages.

        Returns:
            Metadata values indexed by their unique keys.

        Raises:
            ValueError: If brackets, entries or metadata keys are invalid.
        """
        if (
            len(raw_metadata) < 2
            or not raw_metadata.startswith("[")
            or not raw_metadata.endswith("]")
            or "[" in raw_metadata[1:-1]
            or "]" in raw_metadata[1:-1]
        ):
            Parser._raise_parsing_error(
                line_number,
                raw_line,
                "metadata must be enclosed in '[' and ']'",
            )

        content = raw_metadata[1:-1].strip()

        if not content:
            return {}

        metadata: dict[str, str] = {}

        for item in content.split():
            key, separator, value = item.partition("=")

            if not separator or not key or not value:
                Parser._raise_parsing_error(
                    line_number,
                    raw_line,
                    f'invalid metadata entry "{item}"',
                )

            if key not in allowed_keys:
                Parser._raise_parsing_error(
                    line_number,
                    raw_line,
                    f'unknown metadata "{key}"',
                )

            if key in metadata:
                Parser._raise_parsing_error(
                    line_number,
                    raw_line,
                    f'metadata "{key}" is defined more than once',
                )

            metadata[key] = value

        return metadata

    @staticmethod
    def _validate_zone_name(
        name: str,
        line_number: int,
        raw_line: str,
    ) -> None:
        """Reject empty zone names, dashes and whitespace.

        Args:
            name: Zone name to validate.
            line_number: One-based input line number used in error
                messages.
            raw_line: Original input line included in parsing error
                messages.

        Raises:
            ValueError: If the name is empty or contains dashes or
                whitespace.
        """
        if (
            not name
            or "-" in name
            or any(char.isspace() for char in name)
        ):
            Parser._raise_parsing_error(
                line_number,
                raw_line,
                "zone names cannot contain dashes or spaces",
            )

    @staticmethod
    def _format_validation_error(error: ValidationError) -> str:
        """Combine Pydantic validation failures into a readable message.

        Args:
            error: Pydantic validation error whose messages must be
                combined.

        Returns:
            Field names and messages separated by semicolons.
        """
        messages: list[str] = []

        for detail in error.errors():
            field = ".".join(str(value) for value in detail["loc"])

            messages.append(f'{field}: {detail["msg"]}')

        return "; ".join(messages)

    @staticmethod
    def _raise_parsing_error(
        line_number: int,
        line: str,
        cause: str,
    ) -> NoReturn:
        """Raise a parsing error with its line number and offending text.

        Args:
            line_number: One-based input line number used in error
                messages.
            line: Input line to split or include in a parsing error.
            cause: Explanation of why the input line is invalid.

        Raises:
            ValueError: Always, with the contextual parsing error message.
        """
        suffix = f'\nGot: "{line}"' if line else ""

        raise ValueError(
            f"Parsing error at line {line_number}: {cause}{suffix}"
        )
