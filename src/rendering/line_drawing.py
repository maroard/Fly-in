def get_line_points(
    start: tuple[int, int],
    end: tuple[int, int],
) -> list[tuple[int, int]]:
    x1, y1 = start
    x2, y2 = end

    dx = abs(x2 - x1)
    dy = abs(y2 - y1)

    step_x = 1 if x1 < x2 else -1 if x1 > x2 else 0
    step_y = 1 if y1 < y2 else -1 if y1 > y2 else 0

    error = dx - dy

    points: list[tuple[int, int]] = []

    while True:
        points.append((x1, y1))

        if x1 == x2 and y1 == y2:
            break

        double_error = 2 * error

        if double_error > -dy:
            error -= dy
            x1 += step_x

        if double_error < dx:
            error += dx
            y1 += step_y

    return points
