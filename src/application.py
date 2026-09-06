from pathlib import Path

from tuiloom import CommandContext, ScreenContext, TerminalApp, TerminalMenu


class Application:
	def __init__(self) -> None:
		self.app: TerminalApp = TerminalApp("Fly-in")
		self.map: Path | None = None
		self.category_menus: dict[str, TerminalMenu] = {}
		self.main_menu = self._build_main_menu()
		self.map_menu = self._build_map_menu()
		self.app.set_main_menu(self.main_menu)

	def _build_main_menu(self) -> TerminalMenu:
		menu = TerminalMenu(
			self.app,
			ScreenContext(
				menu_name="main",
				title="Main Menu",
				text="Current map: No map selected",
				width=40
			)
		)
		menu.add_command(
			label="Change map",
			behavior=lambda context: context.app.push_menu(self.map_menu)
		)
		return menu

	def _build_map_menu(self) -> TerminalMenu:
		menu = TerminalMenu(
			self.app,
			ScreenContext(
				menu_name="maps",
				title="Map Categories",
				text="Please select a map category:",
				width=40
			)
		)
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
			self.category_menus[folder.name] = category_menu
			menu.add_menu(category_menu, folder.name.capitalize())
		return menu

	def _map_screen(self, menu: TerminalMenu, category_path: Path) -> None:
		maps = sorted(path for path in category_path.iterdir() if path.is_file())
		for map_path in maps:
			def select(
				context: CommandContext,
				selected_map: Path = map_path
			) -> None:
				self.map = selected_map
				self.main_menu.screen_context.text = (
					f"Current map: {category_path.name}/{selected_map.name}"
				)
				context.app.reset_to(self.main_menu)
			menu.add_command(label=map_path.name, behavior=select)

	def run(self) -> None:
		self.app.run(entry_menu=self.map_menu)
