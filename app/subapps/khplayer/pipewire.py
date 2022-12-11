import subprocess
import json

class Node:
	def __init__(self, item):
		self.id = item["id"]
		self.name = item["info"]["props"]["node.name"]
		self.nick = item["info"]["props"].get("node.nick")
		self.description = item["info"]["props"].get("node.description")
		self.media_class = item["info"]["props"].get("media.class","")
		self.inputs = []
		self.outputs = []
	@property
	def label(self):
		if self.nick:
			return self.nick;
		if self.description:
			return self.description;
		return self.name
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

class Patchbay:
	def load(self):
		pwdump = subprocess.Popen(["pw-dump"], stdout=subprocess.PIPE, encoding="utf-8", errors="replace")
		pwconf = json.load(pwdump.stdout)
		print(json.dumps(pwconf, indent=2))

		nodes = {}
		nodes_by_name = {}
		links = []
		
		for item in pwconf:
			#print(item["id"], item["type"])
			info = item.get("info",{})
			props = info.get("props")
			if item["type"] == "PipeWire:Interface:Node":
				node = Node(item)
				nodes[node.id] = node
				nodes_by_name[node.name] = node
			elif item["type"].endswith("PipeWire:Interface:Port"):
				port = Port(item)
				nodes[port.node_id].add_port(port)
			elif item["type"].endswith("PipeWire:Interface:Link"):
				links.append(Link(item))

		self.nodes = nodes.values()
		self.nodes_by_name = nodes_by_name
		self.links = links

	def print(self):
		for node in self.nodes.values():
			if node.media_class.startswith("Audio/"):
				print(node)
		for link in self.links:
			print(link)

	def create_link(self, output_node_id, output_port_id, input_node_id, input_port_id):
		#cmd = ["pw-cli", "create-link", str(output_node_id), str(output_port_id), str(input_node_id), str(input_port_id)]
		cmd = ["pw-link", str(output_port_id), str(input_port_id)]
		print(" ".join(cmd))
		subprocess.run(cmd, check=True)


