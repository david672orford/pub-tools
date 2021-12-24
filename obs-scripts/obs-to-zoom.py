# #! /usr/bin/python3

import logging

logging.basicConfig(
	level=logging.DEBUG,
	format='%(asctime)s %(levelname)s %(name)s %(message)s',
	datefmt='%H:%M:%S'
	)

if __name__ == "__main__":
	from obs2zoom.main import main
	main()
else:
	from obs2zoom.script import MyObsScript
	MyObsScript(globals())
