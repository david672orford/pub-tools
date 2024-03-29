import subprocess
import json
from collections import defaultdict

# Has inputs and outputs
class Node:
	def __init__(self):
		self.id = None
		self.name = None
		self.name_serial = None
		self.nick = None
		self.description = None
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

	def find_port_by_name(self, name):
		for direction in (self.inputs, self.outputs):
			for port in direction:
				if port.name == name:
					return port
		return None

	def __repr__(self):
		return "<Node id=%d nick=%s name=%s media_class=%s inputs=%s outputs=%s>" % (
			self.id,
			self.nick,
			self.name,
			self.media_class,
			self.inputs,
			self.outputs,
			)

# An input or an output
class Port:
	def __init__(self):
		self.id = None
		self.node = None
		self.name = None
		self.direction = None
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

# Connection between an output and an input
class Link:
	def __init__(self):
		self.id = None

	def __repr__(self):
		return "<Link id=%d %s --> %s>" % (
			self.id,
			self.output_port,
			self.input_port,
			)

class Patchbay:
	def load(self):
		pwdump = subprocess.Popen(["pw-dump"], stdout=subprocess.PIPE, encoding="utf-8", errors="replace")

		# It is not clear why, but pw-dump's output can contain multiple JSON objects.
		# It is not clear whether this is a bug or not. The additional objects may
		# represent changes. As observed they always contain one item which has
		# nothing but on ID and a null "info".
		pwconf = pwdump.stdout.read()
		pwconf = "[" + pwconf.replace("\n]\n[\n", "\n],\n[\n") + "]"
		#with open("pw-dump.json", "w") as fh:
		#	fh.write(pwconf)
		pwconf = json.loads(pwconf)
		def pwconf_iter():
			for block in pwconf:
				for item in block:
					yield item

		self.nodes_by_id = {}
		self.nodes_by_name = defaultdict(list)
		self.ports_by_id = {}
		self.links = []
		
		for item in pwconf_iter():
			#print(item["id"], item.get("type"))

			# The body of the record is in the "info" block.
			# Skip null records.
			info = item.get("info",{})
			if info is None:
				continue

			props = info.get("props")

			if item["type"] == "PipeWire:Interface:Node":
				node = Node()
				node.id = item["id"]
				node.name = props["node.name"]
				node.nick = props.get("node.nick")
				node.description = props.get("node.description")
				for key in ("media.class", "media.type"):	# media.type observed on Telegram's "alsoft" node
					if key in props:
						node.media_class = props[key]
						break
				else:
					node.media_class = ""
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
		nlist = self.nodes_by_name[node.name]
		nlist.append(node)
		node.name_serial = len(nlist)

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

	# Find the node specified by attributes
	def find_node(self, **kwargs):
		class NodeTest:
			def __init__(self, **kwargs):
				self.tests = []
				for name, value in kwargs.items():
					self.tests.append(name)
					setattr(self, name, value)
			def __call__(self, node):
				for test in self.tests:
					if getattr(node, test) != getattr(self, test):
						return False
				return True
		node_test = NodeTest(**kwargs)
		for node in self.nodes:
			if node_test(node):
				return node
		return None

	# Find the port specified by ID, or Nodename:Portname.
	# If object is passed, simply return it.
	def find_port(self, port):
		if type(port) is Port:
			return port
		if type(port) is str:
			if not ":" in port:
				raise ValueError(port)
			node_name, port_name = port.split(":",1)
			node = self.find_node(name=node_name)
			return node.find_port_by_name(port_name)
		return self.ports_by_id[port]

	# Find the link specified by the ID's of the ports it connects
	def find_link(self, output_port_id, input_port_id):
		for link in self.links:
			if link.output_port.id == output_port_id and link.input_port.id == input_port_id:
				return link
		return None

	# Create a link between an output and an input. Both are specified
	# in any format understood by .find_port().
	def create_link(self, output_port, input_port):
		output_port = self.find_port(output_port)
		input_port = self.find_port(input_port)

		# Skip if this link already exists
		for link in self.links:
			if link.output_port is output_port and link.input_port is input_port:
				return

		link = Link()
		link.output_port = output_port
		link.input_port = input_port
		cmd = ["pw-link", str(link.output_port.id), str(link.input_port.id)]
		subprocess.run(cmd, check=True)
		self._add_link(link)

	def destroy_link(self, output_port=None, input_port=None, link=None):
		if link is None:
			link = self.find_link(output_port, input_port)
		cmd = ["pw-link", "-d", str(link.id)]
		subprocess.run(cmd, check=True)
		self._remove_link(link)

