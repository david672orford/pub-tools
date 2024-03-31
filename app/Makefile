all:

pot:
	pybabel extract -F translations/babel.cfg -o translations/messages.pot .
	pybabel update -i translations/messages.pot -d translations

poedit:
	poedit translations/ru/LC_MESSAGES/messages.po

mo:
	pybabel compile -d translations

