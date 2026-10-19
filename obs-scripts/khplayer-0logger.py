"""Redirect the Python interpreter's stdour and stderr to log files"""

import os
import sys
import re
import traceback
import threading
import logging

logdir = os.path.join(os.path.dirname(__file__), "..", "instance", "logs")
if not os.path.exists(logdir):
	os.makedirs(logdir)

# Redirect all output so that the script log does not pop up unexpectedly.
class WrapOutput:
	def __init__(self, stdout):
		self.stdout = stdout
		self.script_logs = {}

	def get_script(self):
		name = threading.current_thread().name
		if name.startswith("khplayer-"):
			return name
		for frame in reversed(traceback.extract_stack()):
			m = re.search(r"/(khplayer-.+)\.py$", frame.filename)
			if m and m.group(1) != "khplayer-0logger":
				return m.group(1)
		return None

	def write(self, text):
		script = self.get_script()
		#self.stdout.write(f":::{script}:{text}\n")
		if script is None:
			self.stdout.write(text)
			self.stdout.flush()
		else:
			logfh = self.script_logs.get(script)
			if logfh is None:
				logfh = self.script_logs[script] = open(os.path.join(logdir, script), "w", buffering=1)
			logfh.write(text)

	def flush(self):
		pass

log_file = WrapOutput(sys.stdout)
sys.stdout = log_file
sys.stderr = log_file

logging.basicConfig(
	level = logging.INFO,
	format = "%(asctime)s %(levelname)s %(name)s %(message)s",
	datefmt = "%H:%M:%S",
	stream = sys.stdout,
	)
