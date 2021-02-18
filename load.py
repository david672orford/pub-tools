#! /usr/bin/env python3
from app.models import db, Publications
from app.jwpubs import JWPubs

searcher = JWPubs()
pubs = []
for search_terms in (
		#("библиотека/журналы/", dict(yearFilter="2018")),
		#("библиотека/журналы/", dict(yearFilter="2019")),
		#("библиотека/журналы/", dict(yearFilter="2020")),
		#("библиотека/журналы/", dict(yearFilter="2021")),
		#("библиотека/журналы/", dict(yearFilter="2018")),
		#("библиотека/журналы/", dict(yearFilter="2019")),
		#("библиотека/журналы/", dict(yearFilter="2020")),
		#("библиотека/журналы/", dict(yearFilter="2021")),
		("библиотека/книги/", dict()),
	):
	pubs.extend(searcher.search(*search_terms))

for pub in pubs:
	pubobj = Publications.query.filter_by(code=pub['code'], issue_code=pub.get('issue_code')).one_or_none()
	if pubobj is None:
		pubobj = Publications()
		db.session.add(pubobj)
	for name, value in pub.items():
		setattr(pubobj, name, value)
db.session.commit()

