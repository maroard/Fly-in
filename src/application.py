from pathlib import Path

from tuiloom import CommandContext, ScreenContext, TerminalApp, TerminalMenu


class Application:
	def __init__(self) -> None:
		self.app: TerminalApp = TerminalApp("Fly-in")
		self.main_menu: TerminalMenu
		self.map: Path | None = None
		self._set_main_menu()

	def _set_main_menu(self) -> None:
		self.main_menu = TerminalMenu(
			self.app,
			ScreenContext(
				menu_name="main",
				title="Main Menu",
				text="Please select a map category:",
				width=40
			)
		)

		self.app.set_main_menu(self.main_menu)
		self._map_category_screen()

		if self.map:
			self.main_menu.screen_context.text = (
				f"Map: {self.map.name}"
			)

	def _map_category_screen(self) -> None:
		map_folders = sorted(
			path for path in Path("maps").iterdir() if path.is_dir()
		)
		for folder in map_folders:
			category_menu = TerminalMenu(
				self.app,
				ScreenContext(
					menu_name=f"Category:{folder.name}",
					title=folder.name.capitalize(),
					text="Please select a map:",
					width=40
				)
			)
			self._map_screen(category_menu, folder)
			self.main_menu.add_menu(category_menu, folder.name)

	def _map_screen(self, menu: TerminalMenu, category_path: Path) -> None:
		maps = sorted(path for path in category_path.iterdir() if path.is_file())
		for map_path in maps:
			def select(
				context: CommandContext,
				selected_map: Path = map_path
			) -> None:
				context.menu.screen_context.text = (
					f"Map: {category_path.name}/{selected_map.name}"
				)
				self.map = selected_map
			menu.add_command(label=map_path.name, behavior=select)

	def run(self) -> None:
		self.app.run()
