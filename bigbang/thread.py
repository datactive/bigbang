class Thread:
	def __init__(self, root, known_root=True):
		"""Form a thread object. root: the node of the message that start the thread
		   known_root: indicator whether the root node is in our data set
		"""
		self.root = root
		self.known_root = known_root

	def get_root(self):
		"""Return the root node."""
		return self.root

	def get_num_messages(self):
		"""Return the number of messages in the thread"""
		if(self.known_root):
			return self.root.properties()[0]
		else:
			return 1+self.root.get_successors()[0].properties()[0]

	def get_num_people(self):
		"""Return the number of people in the thread"""
		if(self.known_root):
			return len(self.root.properties()[1])
		else:
			return len(self.root.get_successors()[0].properties()[1])

	def get_duration(self):
		"""Return the time duration of the thread"""
		if(self.known_root):
			r = self.root
		else:
			r = self.root.get_successors()[0]
		l = r.properties()[2]
		l_time = [i.data["Date"] for i in l] 
		l_time.sort()
		return l_time[len(l)-1] - r.data["Date"]
			


class Node:
	def __init__(self, ID, data=None, parent=None):
		"""
		Form a Node object. 
		ID: Message ID, data: Information about that message, parent: the message's reply-to
		"""
		self.id = ID
		self.parent = parent
		self.successors = list()
		self.data = data
		self.processed = False
		self.prop = dict()
	def add_successor(self, successor):
		"""Add a node which has a message that is a reply to this node"""
		self.successors.append(successor)
	def get_id(self):
		"""Return message ID"""
		return self.id
	def get_successors(self):
		"""Return a list of nodes of messages which are replies to this node"""
		return self.successors
	def get_data(self):
		"""Return the Information about this message"""
		return self.data
	def get_parent(self):
		"""Return Information in the data set about this message"""
		return self.parent
	def properties2(self):
		"""Return various properties about the tree with this node as root."""
		visited = set()
		seen_email = set()
		def explore(node):
			num = 1
			duration = 0
			seen_email.add(self.data['From'])
			visited.add(node)
			for s in node.get_successors():
				if(s not in visited):
					seen_email.add(s.data['From'])
					num += explore(s)
			return num
		if(not self.processed):
			num_nodes = explore(self)
			self.prop['num_nodes'] = num_nodes
			self.prop['email_adrress'] = seen_email
			self.processed =  True
		return [self.prop['num_nodes'], self.prop['email_adrress']]

	def properties(self):
		"""Return various properties about the tree with this node as root."""
		visited = set()
		seen_email = set()
		leaves = []
		def explore(node):
			num = 1
			duration = 0
			seen_email.add(node.data['From'])
			visited.add(node)
			if(len(node.get_successors()) == 0):
				leaves.append(node)
			for s in node.get_successors():
				if(s not in visited):
					seen_email.add(s.data['From'])
					num += explore(s)
			return num
		if(not self.processed):
			num_nodes = explore(self)
			self.prop['num_nodes'] = num_nodes
			self.prop['email_adrress'] = seen_email
			self.prop['leaves'] = leaves
			self.processed =  True
		return [self.prop['num_nodes'], self.prop['email_adrress'], self.prop['leaves']]
