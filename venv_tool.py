#! /usr/bin/python3
"""
Virtual environment creation and activation
"""

# References:
# * [venv — Creation of virtual environments](https://docs.python.org/3/library/venv.html)
# * [PEP 405 – Python Virtual Environments](https://peps.python.org/pep-0405/)
# * [site — Site-specific configuration hook](https://docs.python.org/3/library/site.html)
# * [Install packages in a virtual environment using pip and venv](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)
# * [Python Virtual Environments: A Primer](https://realpython.com/python-virtual-environments-a-primer/)
# * [Activate a virtualenv with a Python script](https://stackoverflow.com/questions/6943208/activate-a-virtualenv-with-a-python-script#answer-68173529)

import os
import sys

venv_dir = os.path.join(os.path.dirname(__file__), ".venv")

def activate(dist_packages=False):
	"""
	If we have a Python virtual environment, activate it.
	"""
	if os.path.exists(os.path.join(venv_dir, "pyvenv.cfg")):
		sys.prefix = sys.exec_prefix = os.path.abspath(venv_dir)
	
		# Drop packages added by the Linux distribution from the path
		if not dist_packages:
			sys.path = list(filter(lambda item: not item.endswith("/dist-packages"), sys.path))
	
		# Add packages from the virtual environment to the path
		import site
		if sys.platform == "win32":
			site_packages = os.path.join(base, "Lib", "site-packages")
		else:
			site_packages = os.path.join(sys.prefix, f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
		site.addsitedir(site_packages)

	#print(sys.path)

if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--create", action="store_true", help="Create a virtual environment")
	parser.add_argument("--update", action="store_true", help="Update the virtual environment")
	parser.add_argument("--delete", action="store_true", help="Delete the virtual environment")
	options = parser.parse_args()

	# Install or upgrade the virtual environment
	if options.create:
		if os.path.exists(venv_dir):
			print("Already exists")
			sys.exit(1)
		import venv
		venv.create(venv_dir, with_pip=True)
	elif options.update:
		import venv
		venv.create(venv_dir, upgrade_deps=True)

	# Install or upgrade the packages listed in requirements.txt
	if options.create or options.update:
		activate()
		import subprocess
		subprocess.check_call([os.path.join(venv_dir, "bin", "python"), "-m", "pip", "install", "-r", "requirements.txt"])

	elif options.delete:
		import shutil
		shutil.rmtree(venv_dir)

	else:
		parser.print_help()


