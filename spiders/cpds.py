import requests
import re
import json
import bs4
from datetime import datetime
import rdate
import os
import hashlib
from urllib.parse import urlparse
from os.path import basename
import time
from progress import Progress
from source import Source

NOW = datetime.now()

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

class Cpds(Source):
	def __init__(self, config, progress, changes):
		Source.__init__(self, config, progress, changes)
		self.config = config
		self.html = None
		self.outdir = "wiki-cpds"

	def login(self):
		s = requests.session()
		url0 = 'https://raco.fib.upc.edu/cas/login?service=http://wiki.fib.upc.es/cpds/index.php?title=Especial:Registre_i_entrada&returnto=P%C3%A0gina_principal'
		r0 = s.get(url0)
		#cookies0 = r0.cookies.get_dict()

		m = re.search('/cas/login[^"]*', r0.text)
		dir1 = m.group()
		url1 = 'https://raco.fib.upc.edu' + dir1
#		url1 = 'http://localhost:8888' + dir1
		lt = re.search('name="lt" value="([^"]*)', r0.text).groups()[0]
		d1 = {}
		d1['username'] = self.config['username']
		d1['password'] = self.config['password']
		d1['_eventId'] = 'submit'
		d1['lt'] = lt
		r1 = s.post(url1, data = d1)
		#print(r1.text)
		self.html = r1.text
		self.session = s

	def parse(self):
		#print('Parsing subject {} with code {}'.format(name, code))
		url = 'http://wiki.fib.upc.es/cpds/index.php/P%C3%A0gina_principal'
		s = self.session
		#print(url)
		self.pr.add(1)
		html = s.get(url).text
		self.pr.step()
		soup = bs4.BeautifulSoup(html, 'lxml')
		#print(soup)
		links = soup.findAll('a', {'class':'external'})
		self.pr.add(len(links))
		for i in range(len(links)):
			a = links[i]
			self.parse_link(a)
			self.pr.step()


	def update_counting(self, i, n):
		print('\rCounting objects ({}/{})'.format(i, n),
			end='', flush=True)
		if i==n: print()

	def update_retrieve(self, i, n):
		print('\rRetrieving objects ({}/{})'.format(i, n),
			end='', flush=True)
		if i==n: print()

	def parse_link(self, a):
		s = self.session
		maybe_href = a['href']
		entries = re.findall(
			'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
			maybe_href)

		if len(entries) != 1: return
		href = entries[0]
		if not href.startswith('http://wiki.fib.upc.es/cpds/'): return
		url = href
		filename = basename(urlparse(url)[2])
		#print(a.text)
		#print(url)
		#print(filename)

		file_path = self.outdir + '/' + filename

		resp_head = s.head(href)
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

		resp = s.get(href)

		with open(file_path, 'wb') as f:
			f.write(resp.content)

		if 'Last-Modified' in resp.headers:
			last = resp.headers['Last-Modified']
			t = time.mktime((time.strptime(last, "%a, %d %b %Y %H:%M:%S GMT")))
			os.utime(file_path, (t,t))

		if new_version:
			self.changes.mod(file_path)
		else:
			self.changes.new(file_path)


	def update(self):
		self.login()
		self.parse()

	def status(self): pass


#with open('config.json','r') as f:
#	config = json.load(f)
#
#r = Cpds(config)
#r.login()
##with open('raco.html','r') as f:
##	r.html = f.read()
#
#r.parse()
