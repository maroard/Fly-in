from src.simulation import Movement


def format_turn(movements: list[Movement]) -> str:
    return " ".join(
        f"D-{movement.drone_id}-{movement.destination}"
        for movement in movements
    )
