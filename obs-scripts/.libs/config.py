import os, sqlite3, json

dbfile = os.path.join(os.path.dirname(__file__), "..", "..", "instance", "pub-tools.db")

def get_config(name):
	conn = sqlite3.connect(dbfile)
	result = conn.execute("SELECT data from config where name = ?", (name,))
	data = result.fetchone()
	result.close()
	conn.close()
	if data is not None:
		return json.loads(data[0])
	return {}

def put_config(name, data):
	conn = sqlite3.connect(dbfile)
	result = conn.execute("INSERT OR REPLACE INTO config (name, data) values (?, ?)", (name, json.dumps(data)))
	assert result.rowcount == 1
	conn.commit()
	result.close()
	conn.close()

