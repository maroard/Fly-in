from src.application import Application


def main() -> None:
	try:
		app = Application()
		app.run()
	except Exception as error:
		raise Exception(f"Error: {error}")


if __name__ == "__main__":
	raise SystemExit(main())
