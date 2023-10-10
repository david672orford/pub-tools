all:

pot:
	pybabel extract -F translations/babel.cfg -o translations/messages.pot .
	pybabel update -i translations/messages.pot -d translations

mo:
	pybabel compile -d translations
