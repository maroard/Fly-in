"""Start the Fly-in terminal application."""

from src.application import Application


def main() -> None:
    """Run the terminal application and report startup errors."""
    try:
        app = Application()

        app.run()
    except Exception as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()
