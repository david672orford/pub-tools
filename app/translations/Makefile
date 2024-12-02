all:

pot:
	pybabel extract -F babel.cfg -o messages.pot ..
	pybabel update -i messages.pot -d .

poedit:
	poedit ru/LC_MESSAGES/messages.po

mo:
	pybabel compile -d .

