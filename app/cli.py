import os

from rich.console import Console
from rich.table import Table

def init_app(app):
	@app.cli.command("subapps")
	def cmd_subapps():
		"""List Pub-Tools subapps"""
		subappsdir = os.path.join(os.path.dirname(__file__), "subapps")
		table = Table(show_header=True, title="Subapps of Pub-Tools", show_lines=True)
		table.add_column("Subapp")
		table.add_column("Status")
		for subapp in os.listdir(subappsdir):
			if not subapp.startswith("__"):
				table.add_row(subapp, "Enabled" if subapp in app.config["ENABLED_SUBAPPS"] else "Disabled")
		Console().print(table)
