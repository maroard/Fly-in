"""Store and assemble styled terminal character grids."""

from tuiloom import display_width


class Canvas:
    """Store styled terminal characters in a rectangular grid.

    Attributes:
        width: Number of terminal columns.
        height: Number of terminal rows.
        grid: Rows of individual display-width-one character strings.
    """

    def __init__(self, width: int, height: int) -> None:
        """Create a grid filled with spaces.

        Args:
            width: Available width in terminal columns.
            height: Available height in terminal rows.
        """
        self.width = width
        self.height = height

        self.grid: list[list[str]] = [
            [" "] * self.width
            for _ in range(self.height)
        ]

    def set(self, x: int, y: int, char: str) -> None:
        """Replace one cell with a character of display width one.

        Args:
            x: Zero-based grid column.
            y: Zero-based grid row.
            char: Character, optionally styled, with a display width of one
                cell.

        Raises:
            ValueError: If the character width is not one or coordinates
                are out of bounds.
        """
        if display_width(char) != 1:
            raise ValueError(
                "Canvas.set() expects exactly one character; "
                f'received "{char}" ({len(char)} characters).'
            )

        if not 0 <= x < self.width:
            raise ValueError(
                f"Canvas x-coordinate out of bounds: {x}. "
                f"Expected a value between 0 and {self.width - 1}."
            )

        if not 0 <= y < self.height:
            raise ValueError(
                f"Canvas y-coordinate out of bounds: {y}. "
                f"Expected a value between 0 and {self.height - 1}."
            )

        self.grid[y][x] = char

    def write(self, x: int, y: int, text: str) -> None:
        """Write a nonempty string across consecutive cells on one row.

        Args:
            x: Zero-based grid column.
            y: Zero-based grid row.
            text: Nonempty text written from the specified grid position.

        Raises:
            ValueError: If text is empty, exceeds the row or contains
                invalid cell data.
        """
        if not text:
            raise ValueError(
                "Canvas.write() cannot write an empty string."
            )

        if x + len(text) > self.width:
            raise ValueError(
                "Canvas.write() text exceeds the canvas width: "
                f'writing "{text}" at x={x} requires columns '
                f"{x} to {x + len(text) - 1}, but the last valid "
                f"column is {self.width - 1}."
            )

        for i, char in enumerate(text):
            self.set(x + i, y, char)

    def get(self, x: int, y: int) -> str:
        """Return the character stored at a grid position.

        Args:
            x: Zero-based grid column.
            y: Zero-based grid row.

        Returns:
            Stored character, including any terminal style sequences.

        Raises:
            IndexError: If the indices are outside the grid Python indexing
                bounds.
        """
        return self.grid[y][x]

    def to_lines(self) -> list[str]:
        """Join the grid rows into terminal output lines.

        Returns:
            One joined string per grid row, preserving terminal styles.
        """
        return ["".join(line) for line in self.grid]
