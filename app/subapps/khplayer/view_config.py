from flask import render_template, request, redirect
import re
import os
import subprocess
from time import sleep
import logging

from .views import blueprint
from . import menu
from ...utils.babel import gettext as _
from .utils.pipewire import Patchbay

logger = logging.getLogger(__name__)

menu.append((_("Config"), "/config/"))

@blueprint.route("/config/")
def page_config():
	patchbay = Patchbay()
	patchbay.load()
	return render_template(
		"khplayer/config.html",
		patchbay = patchbay,
		top = ".."
		)

@blueprint.route("/config/save", methods=["POST"])
def page_config_save():
	patchbay = Patchbay()
	patchbay.load()
	data = request.form.to_dict()
	rules = []
	for name, value in data.items():
		m = re.match(r"^([^-]+)-(\d+)-nick$", name)
		if m:
			obj_type = m.group(1)
			id = int(m.group(2))
			if obj_type == "device":
				name = patchbay.devices_by_id[id].name
			else:
				name = patchbay.nodes_by_id[id].name
			nick = value
			description = data[f"{obj_type}-{id}-description"]
			rule = """
table.insert(alsa_monitor.rules, {
	matches = {
		{
			{ "_OBJ_TYPE_.name", "equals", "_NAME_" },
		},
	},
    apply_properties = {
		["_OBJ_TYPE_.nick"] = "_NICK_",
		["_OBJ_TYPE_.description"] = "_DESCRIPTION_"
	},
})
""".lstrip().replace("_OBJ_TYPE_",obj_type).replace("_NAME_",name).replace("_NICK_",nick).replace("_DESCRIPTION_",description)
			rules.append(rule)

	configdir = os.path.join(os.environ["HOME"], ".config", "wireplumber", "main.lua.d")
	configfile = os.path.join(configdir, "51-alsa-rename.lua")
	os.makedirs(configdir, exist_ok=True)
	with open(configfile, "w") as fh:
		fh.write("\n".join(rules))

	subprocess.run(["systemctl", "--user", "restart", "wireplumber"], check=True)
	sleep(2)

	return redirect(".")
