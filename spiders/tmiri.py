import requests
import bs4, os
from source import Source
from os.path import basename
from urllib.parse import urlparse
import time

class Tmiri(Source):
	def __init__(self, config, progress, changes):
		Source.__init__(self, config, progress, changes)
		self.session = requests.session()
		self.outdir = 'tmiri'

	def parse(self):
		self.pr.add(1)
		url = 'http://www.cs.upc.edu/~larrosa/tmiri.html'
		s = self.session
		html = s.get(url).text
		self.pr.step()
		soup = bs4.BeautifulSoup(html, 'lxml')

		list_links = soup.findAll('a')
		self.pr.add(len(list_links))
		for a in list_links:
			#print(a['href'])
			self.parse_link(a)
			self.pr.step()

	def parse_link(self, a):
		s = self.session
		href = a['href']
		start = 'MIRI-TMIRI-files'
		if not href.startswith(start):
			return
		url = 'http://www.cs.upc.edu/~larrosa/' + href
		filename = basename(urlparse(url)[2])
		#print(a.text)
		#print(url)
		#print(filename)

		file_path = self.outdir + '/' + filename

		resp_head = s.head(url)
		new_version = False
		if 'Last-Modified' in resp_head.headers:
			if os.path.isfile(file_path):
				t_local = os.path.getmtime(file_path)
				last_remote = resp_head.headers['Last-Modified']
				t_remote = time.mktime((time.strptime(last_remote, "%a, %d %b %Y %H:%M:%S GMT")))
				if t_local >= t_remote:
					# The local file is newer or equal than the remote. Skip
					return
				else:
					# The local file is older than the remote. Was modified
					new_version = True

		resp = s.get(url, stream=True)

		with open(file_path, 'wb') as f:
			for chunk in resp.iter_content(chunk_size=1024*1024): 
				if chunk: # filter out keep-alive new chunks
					f.write(chunk)

		if 'Last-Modified' in resp.headers:
			last = resp.headers['Last-Modified']
			t = time.mktime((time.strptime(last, "%a, %d %b %Y %H:%M:%S GMT")))
			os.utime(file_path, (t,t))

		if new_version:
			self.changes.mod(file_path)
		else:
			self.changes.new(file_path)

	def update(self):
		self.parse()

#l = Larrosa()
#l.parse()
