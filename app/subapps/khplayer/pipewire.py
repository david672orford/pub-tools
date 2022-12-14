import subprocess
import json

class Node:
	def __init__(self):
		self.id = None
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
	def __init__(self):
		self.id = None
		self.links = []

	def add_link(self, link):
		self.links.append(link)

	def remove_link(self, link):
		self.links.remove(link)

	def __repr__(self):
		return "<Port id=%d name=%s direction=%s>" % (
			self.id,
			self.name,
			self.direction,
			)

class Link:
	def __init__(self):
		self.id = None

	def __repr__(self):
		return "<Link id=%d %s --> %s>" % (
			self.id,
			self.input_port,
			self.output_port,
			)

class Patchbay:
	def load(self):
		pwdump = subprocess.Popen(["pw-dump"], stdout=subprocess.PIPE, encoding="utf-8", errors="replace")
		pwconf = json.load(pwdump.stdout)
		#print(json.dumps(pwconf, indent=2))

		self.nodes_by_id = {}
		self.nodes_by_name = {}
		self.ports_by_id = {}
		self.links = []
		
		for item in pwconf:
			#print(item["id"], item["type"])
			info = item.get("info",{})
			props = info.get("props")
			if item["type"] == "PipeWire:Interface:Node":
				node = Node()
				node.id = item["id"]
				node.name = props["node.name"]
				node.nick = props.get("node.nick")
				node.description = props.get("node.description")
				node.media_class = props.get("media.class","")
				self._add_node(node)
			elif item["type"].endswith("PipeWire:Interface:Port"):
				port = Port()
				port.id = item["id"]
				port.name = props["port.name"]
				port.direction = info["direction"]
				port.node = self.nodes_by_id[props["node.id"]]
				self._add_port(port)
			elif item["type"].endswith("PipeWire:Interface:Link"):
				link = Link()
				link.id = item["id"]
				link.input_port = self.ports_by_id[info["input-port-id"]]
				link.output_port = self.ports_by_id[info["output-port-id"]]
				self._add_link(link)

		self.nodes = self.nodes_by_id.values()

	def print(self):
		for node in self.nodes:
			if "Audio" in node.media_class:
				print(node)
		for link in self.links:
			print(link)

	def _add_node(self, node):
		self.nodes_by_id[node.id] = node
		self.nodes_by_name[node.name] = node

	def _add_port(self, port):
		port.node.add_port(port)
		self.ports_by_id[port.id] = port

	def _add_link(self, link):
		link.input_port.add_link(link)
		link.output_port.add_link(link)
		self.links.append(link)

	def _remove_link(self, link):
		link.input_port.remove_link(link)
		link.output_port.remove_link(link)
		self.links.remove(link)

	# Find the port specified by port ID
	def find_port(self, port_id):
		return self.ports_by_id[port_id]

	# Find the link specified by the ID's of the ports it connects
	def find_link(self, output_port_id, input_port_id):
		for link in self.links:
			if link.output_port.id == output_port_id and link.input_port.id == input_port_id:
				return link
		else:
			raise KeyError

	def create_link(self, output_port_id, input_port_id):
		cmd = ["pw-link", str(output_port_id), str(input_port_id)]
		subprocess.run(cmd, check=True)
		self.load()
		link = Link()
		link.output_port = self.find_port(output_port_id)
		link.input_port = self.find_port(input_port_id)
		self._add_link(link)

	def destroy_link(self, output_port_id, input_port_id):
		self.load()
		link = self.find_link(output_port_id, input_port_id)
		cmd = ["pw-link", "-d", str(link.id)]
		subprocess.run(cmd, check=True)
		self._remove_link(link)

