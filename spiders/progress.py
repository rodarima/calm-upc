class Progress:
	def __init__(self):
		self.n_objects = 0
		self.i_objects = 0

	def add(self, i):
		self.n_objects += i

	def step(self):
		self.i_objects += 1
		self.update(self.i_objects, self.n_objects)

	def end(self):
		print()
		if self.i_objects != self.n_objects:
			print("BUG: self.i_objects != self.n_objects")

	def update(self, i, n):
		print('\rRetrieving objects ({}/{})'.format(i, n),
			end='', flush=True)
