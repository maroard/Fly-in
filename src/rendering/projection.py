class Projector:
    def __init__(
        self,
        min_x: int,
        max_x: int,
        min_y: int,
        max_y: int,
        width: int,
        height: int
    ):
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y
        self.width = width
        self.height = height

    def project(self, x: int, y: int) -> tuple[int, int]:
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
                (1 - (
                    (y - self.min_y)
                    / (self.max_y - self.min_y)
                ))
                * (self.height - 1)
            )

        return screen_x, screen_y
