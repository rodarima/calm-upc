from raco import Raco
from cpds import Cpds
from progress import Progress
from source import Source
from changes import Changes
from tmiri import Tmiri
import json

with open('config.json','r') as f:
	config = json.load(f)

progress = Progress()
changes = Changes()

sources = [
	Tmiri(config, progress, changes),
	Cpds(config, progress, changes),
	Raco(config, progress, changes)
]

for source in sources:
	source.update()

progress.end()

changes.status()

#for source in sources:
#	source.status()
