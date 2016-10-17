import requests
import re
import json
import bs4
from datetime import datetime
import rdate
import os
import hashlib

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

class Raco:
	def __init__(self, config):
		self.config = config
		self.html = None
	def login(self):
		s = requests.session()
		url0 = 'https://raco.fib.upc.edu/cas/login?service=https%3A%2F%2Fraco.fib.upc.edu%2F'
		r0 = s.get(url0)
		#cookies0 = r0.cookies.get_dict()

		m = re.search('/cas/login[^"]*', r0.text)
		dir1 = m.group()
		url1 = 'https://raco.fib.upc.edu' + dir1
#		url1 = 'http://localhost:8888' + dir1
		lt = re.search('name="lt" value="([^"]*)', r0.text).groups()[0]
		d1 = {}
		d1['username'] = config['username']
		d1['password'] = config['password']
		d1['_eventId'] = 'submit'
		d1['lt'] = lt
		r1 = s.post(url1, data = d1)
		#print(r1.text)
		self.html = r1.text
		self.session = s

	def parse(self):
		soup = bs4.BeautifulSoup(self.html, 'lxml')
		subjects = soup.find('li', {'class':'normal assignatures'}).find('ul').findAll('a')

		changelog = {}
		data = {}
		for subject in subjects:
			name = subject.text
			href = subject['href']
			end_name = re.search('\((.*)\)', name).groups()[0]
			final_name = end_name.split('-')[0].lower()
			code = re.search('espai=(.*)', href).groups()[0]
#			print('Subject found {} with code {}'.format(final_name, code))
			entries = self.parse_subject(final_name, code, changelog)
			data[final_name] = entries
			#break
		#print(json.dumps(changelog, indent=2))
		#print(json.dumps(data, indent=2))

	def parse_subject(self, name, code, changelog):
		#print('Parsing subject {} with code {}'.format(name, code))
		url = 'https://raco.fib.upc.edu/avisos/llista.jsp?espai=' + code
		s = self.session
		html = s.get(url).text
		soup = bs4.BeautifulSoup(html, 'lxml')
		ul = soup.find('ul',{'class':'avisos'})
		#print(ul)
		entries = []
		#changelog = {}
		for li in ul.findAll('li'):
			desc = li.find('p')
			date_str = desc.find('span').text
			href = desc.find('a')
			title = href['title']
			date = datetime.strptime(date_str, '%d/%m/%Y')
			rd = rdate.rdate(date)
#			print(rdate.rdate(date) + '\t' + title)
			entry = {}
			entry['title'] = title
			entry['subject'] = name
			entry['a'] = 'https://raco.fib.upc.edu' + href['href']
			#if not rd in changelog: changelog[rd] = []
			#changelog[rd].append(entry)

			#print(date_str)
			self.parse_entry(entry)
			entries.append(entry)
		return entries
	
	def parse_entry(self, entry):
		url = entry['a']
		s = self.session
		r = s.get(url)
		html = r.text
		soup = bs4.BeautifulSoup(html, 'lxml')
		cont = soup.find('div',{'class':'dintre_contingut'})
		descs = cont.findAll('p', recursive=False)[1:-2]
		desc = ''
		for p in descs:
			desc += '{}\n'.format(p.text)
		#print(desc)
		entry['desc'] = desc
		#print(cont)
		attachments = []
		attach = cont.find('div',{'class':'post-attachments'})
		if attach != None:
			for li in attach.findAll('li'):
				attachment = {}
				a = li.find('a')
				attachment['name'] = a.text
				attachment['url'] = 'https://raco.fib.upc.edu' + a['href']
				self.download_file(entry, attachment)
				attachments.append(attachment)
		entry['attachments'] = attachments

	def download_file(self, entry, attachment):
		subject = entry['subject']
		url = attachment['url']
		filename = attachment['name']
		#print('Downloading {}'.format(filename))
		s = self.session

		r = s.get(url)
		tmpf = '/tmp/raco.tmp'

		with open(tmpf, 'wb') as f:
			f.write(r.content)

		md5_new = md5(tmpf)

		filepath = 'raco/' + subject + '/' + filename

		if not os.path.exists(os.path.dirname(filepath)):
			os.makedirs(os.path.dirname(filepath))
		
		if os.path.isfile(filepath):
			md5_old = md5(filepath)
			if md5_old != md5_new:
				print("New version of the file "+filepath)
				with open(filepath, 'wb') as f:
					f.write(r.content)
		else:
			print("New file "+filepath)
			with open(filepath, 'wb') as f:
				f.write(r.content)


with open('config.json','r') as f:
	config = json.load(f)

r = Raco(config)
r.login()
#with open('raco.html','r') as f:
#	r.html = f.read()

r.parse()
