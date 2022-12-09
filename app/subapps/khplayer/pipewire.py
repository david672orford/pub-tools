import subprocess
import json

pwdump = subprocess.Popen(["pw-dump"], stdout=subprocess.PIPE, encoding="utf-8", errors="replace")
pwconf = json.load(pwdump.stdout)

nodes = {}
links = []

class Node:
	def __init__(self, item):
		self.id = item["id"]
		self.name = item["info"]["props"]["node.name"]
		self.nick = item["info"]["props"].get("node.nick")
		self.media_class = item["info"]["props"].get("media.class","")
		self.inputs = []
		self.outputs = []
	def add_port(self, port):
		if port.direction == "input":
			self.inputs.append(port)
		elif port.direction == "output":
			self.outputs.append(port)
		else:
			raise AssertionError
	def __repr__(self):
		return "<Node id=%d nick=%s name=%s inputs=%s outputs=%s>" % (
			self.id,
			self.nick,
			self.name,
			self.inputs,
			self.outputs,
			)

class Port:
	def __init__(self, item):
		self.id = item["id"]
		self.name = item["info"]["props"]["port.name"]
		self.direction = item["info"]["direction"]
		self.node_id = item["info"]["props"]["node.id"]
	def __repr__(self):
		return "<Port id=%d name=%s direction=%s>" % (
			self.id,
			self.name,
			self.direction,
			)

class Link:
	def __init__(self, item):
		self.id = item["id"]
		info = item["info"]
		self.input_node_id = info["input-node-id"]
		self.input_port_id = info["input-port-id"]
		self.output_node_id = info["output-node-id"]
		self.output_port_id = info["output-port-id"]
	def __repr__(self):
		return "<Link id=%d %d %d --> %d %d>" % (
			self.id,
			self.input_node_id,
			self.input_port_id,
			self.output_node_id,
			self.output_port_id,
			)

#print(json.dumps(pwconf, indent=2))
for item in pwconf:
	#print(item["id"], item["type"])
	info = item.get("info",{})
	props = info.get("props")
	if item["type"] == "PipeWire:Interface:Node":
		nodes[item["id"]] = Node(item)
	elif item["type"].endswith("PipeWire:Interface:Port"):
		port = Port(item)
		nodes[port.node_id].add_port(port)
	elif item["type"].endswith("PipeWire:Interface:Link"):
		links.append(Link(item))

for node in nodes.values():
	if node.media_class.startswith("Audio/"):
		print(node)

for link in links:
	print(link)

