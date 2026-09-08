class Canvas:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.grid: list[list[str]] = [
            [" "] * self.width
            for _ in range(self.height)
        ]

    def set(self, x: int, y: int, char: str) -> None:
        if len(char) != 1:
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
        return self.grid[y][x]

    def to_lines(self) -> list[str]:
        return ["".join(line) for line in self.grid]
