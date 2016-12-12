class Changes:
	def __init__(self):
		self.fnew = []
		self.fmod = []

	def mod(self, f):
			self.fmod.append(f)

	def new(self, f):
			self.fnew.append(f)

	def print_files(self):
		for f in self.fnew:
			print("NEW\t{}".format(f))
		for f in self.fmod:
			print("MOD\t{}".format(f))

	def status(self):
		new = len(self.fnew)
		mod = len(self.fmod)
		if new == 0 and mod == 0:
			print("Already up-to-date.")
		else:
			print()
			self.print_files()
			print()
			new_s = "s"
			mod_s = "s"
			if new == 1: new_s = ""
			if mod == 1: mod_s = ""

			if new == 0:
				print("{} modified file{}.".format(mod, mod_s))
			elif mod == 0:
				print("{} new file{}.".format(new, new_s))
			else:
				print("{} new file{} and {} modified.".format(new, new_s, mod))
