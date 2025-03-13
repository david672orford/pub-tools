from flask import render_template, request, redirect
import re
import os
import json
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
	#patchbay.print()

	data = request.form.to_dict()
	rules = []
	for key, value in data.items():
		m = re.match(r"^([^-]+)-(\d+)-nick$", key)
		if m:
			obj_type = m.group(1)
			id = int(m.group(2))
			print(obj_type)
			obj = patchbay.devices_by_id[id] if obj_type == "device" else patchbay.nodes_by_id[id]
			nick = value.strip()
			description = data[f"{obj_type}-{id}-description"].strip()
			disabled = data.get(f"{obj_type}-{id}-disabled")
			monitor_disabled = data.get(f"{obj_type}-{id}-monitor-disabled")
			props = {}
			if nick:
				props[f"{obj_type}.nick"] = nick
			if description:
				props[f"{obj_type}.description"] = description
			if disabled:
				props[f"{obj_type}.disabled"] = True
			# FIXME: none of these attempts work
			#if monitor_disabled:
			#	props["node.features.audio.monitor-ports"] = False
			#	#props["item.features.monitor"] = False
			rules.append({
				"matches": [
				 	{ f"{obj_type}.name": obj.name }
				],
				"actions": {
					"update-props": props
				}
			})

	configdir = os.path.join(os.environ["HOME"], ".config", "wireplumber", "wireplumber.conf.d")
	configfile = os.path.join(configdir, "99-alsa-rename.conf")
	os.makedirs(configdir, exist_ok=True)
	with open(configfile, "w") as fh:
		fh.write('\"monitor.alsa.rules\": ')
		json.dump(rules, fh, indent=2)

	subprocess.run(["systemctl", "--user", "restart", "wireplumber"], check=True)
	sleep(2)

	return redirect(".")
