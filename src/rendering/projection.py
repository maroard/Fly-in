"""Scale graph coordinates into terminal panel dimensions."""


class Projector:
    """Convert graph coordinates into cells of a terminal panel.

    Attributes:
        min_x: Minimum graph x coordinate.
        max_x: Maximum graph x coordinate.
        min_y: Minimum graph y coordinate.
        max_y: Maximum graph y coordinate.
        width: Target terminal width in cells.
        height: Target terminal height in cells.
    """

    def __init__(
        self,
        min_x: int,
        max_x: int,
        min_y: int,
        max_y: int,
        width: int,
        height: int
    ) -> None:
        """Store graph bounds and target panel dimensions.

        Args:
            min_x: Smallest horizontal coordinate in the graph.
            max_x: Largest horizontal coordinate in the graph.
            min_y: Smallest vertical coordinate in the graph.
            max_y: Largest vertical coordinate in the graph.
            width: Available width in terminal columns.
            height: Available height in terminal rows.
        """
        self.min_x = min_x
        self.max_x = max_x

        self.min_y = min_y
        self.max_y = max_y

        self.width = width
        self.height = height

    def project(self, x: int, y: int) -> tuple[int, int]:
        """Scale a point into the panel and invert its vertical axis.

        Args:
            x: Horizontal graph coordinate.
            y: Vertical graph coordinate.

        Returns:
            Column and row, centered on an axis whose graph extent is zero.
        """
        if self.min_x == self.max_x:
            screen_x = self.width // 2
        else:
            screen_x = round(
                (x - self.min_x)
                / (self.max_x - self.min_x)
                * (self.width - 1)
            )

        if self.min_y == self.max_y:
            screen_y = self.height // 2
        else:
            screen_y = round(
                (
                    1 - (
                        (y - self.min_y)
                        / (self.max_y - self.min_y)
                    )
                )
                * (self.height - 1)
            )

        return screen_x, screen_y
