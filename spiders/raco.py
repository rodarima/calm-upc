import requests
import re
import json
import bs4
from datetime import datetime
import rdate
import os
import hashlib
import textwrap
import time
from progress import Progress
from source import Source

NOW = datetime.now()
FORMAT_DATE = '%Y-%m-%d'

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

class Raco(Source):
	def __init__(self, config, progress, changes):
		Source.__init__(self, config, progress, changes)
		self.config = config
		self.html = None
		self.data = None
		self.raco_errors = 0

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
		d1['username'] = self.config['username']
		d1['password'] = self.config['password']
		d1['_eventId'] = 'submit'
		d1['lt'] = lt
		self.pr.add(1)
		r1 = s.post(url1, data = d1)
		self.pr.step()
		#print(r1.text)
		self.html = r1.text
		self.session = s

	def parse(self):
		soup = bs4.BeautifulSoup(self.html, 'lxml')
		subjects = soup.find('li', {'class':'normal assignatures'}).find('ul').findAll('a')

		changelog = {}
		data = {}
		self.pr.add(len(subjects) * 2)
		for i in range(len(subjects)):
			subject = subjects[i]
			sub = {}
			name = subject.text
			href = subject['href']
			end_name = re.search('\((.*)\)', name).groups()[0]
			final_name = end_name.split('-')[0].lower()
			code = re.search('espai=(.*)', href).groups()[0]
			sub['name'] = final_name
			sub['code'] = code
#			print('Subject found {} with code {}'.format(final_name, code))
			sub['assignments'] = self.parse_assignments(final_name, code, changelog)
			sub['notices'] = self.parse_notices(final_name, code, changelog)
			data[final_name] = sub
			#break
		#print(json.dumps(changelog, indent=2))
		with open('raco/all.txt', 'w') as f:
			json.dump(data, f)

		self.data = data

		self.update_stored(data)

	def search_assignments(self, tree):
		all_assignments = []
		for name in tree:
			sub = tree[name]
			assignments = sub['assignments']
			if assignments == None: continue
			for assign in assignments:
				assign['subject'] = name
				all_assignments.append(assign)

		N = len(all_assignments)
		if N == 0: return
		print()
		print("You have {} pending assignments:".format(N))
		for assign in all_assignments:
			sub = assign['subject']
			title = assign['title']
			due = datetime.strptime(assign['due_date'], '%Y-%m-%d %H:%M:%S')
			diff = due - NOW
			hours = diff.seconds / 3600 / 24
			left = "{:.1f}".format(diff.days + hours).zfill(4)
			print("{} days left. {}: {}".format(left, sub, title))
				

	def parse_assignments(self, name, code, changelog):
		#print('Parsing subject {} with code {}'.format(name, code))
		url = 'https://raco.fib.upc.edu/practiques/llista.jsp?espai=' + code
		s = self.session
		#print(url)
		html = s.get(url).text
		self.pr.step()
		soup = bs4.BeautifulSoup(html, 'lxml')
		table = soup.find('table', {'id':'practiques_actuals'})
		if table == None: # No assignments
			return []

		tr_list = table.findAll('tr')

		assignments = []

		list_rows = tr_list[1:]
		for tr in list_rows:
			td_list = tr.findAll('td')
			td_title = td_list[0]
			a_assign = td_title.find('a')
			if a_assign == None:
				continue
			td_date = td_list[1] #09/11/2016 23:59
			date_str = td_date.text.strip()
			date = datetime.strptime(date_str, '%d/%m/%Y %H:%M')

			url_assign = a_assign['href']
			name_assign = a_assign['title']
			assign = {}
			assign['url'] = 'https://raco.fib.upc.edu' + url_assign
			assign['title'] = name_assign
			assign['due_date'] = str(date)
			self.pr.add(1)
			assignments.append(self.parse_assignment(assign))

		return assignments

	def parse_assignment_date(self, date_str):
		months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
		l = date_str.split()

		day = int(l[1])
		year = int(l[5])
		month = months.index(l[3][0:3]) + 1
		if len(l) == 7:
			time = l[6]
			tl = time.split(':')
			hour = int(tl[0])
			minu = int(tl[1])
			date = datetime(year, month, day, hour, minu)
		else:
			date = datetime(year, month, day)
			
		#print(date_str, date)
		return date

	def parse_assignment(self, assign):
		s = self.session
		html = s.get(assign['url']).text
		self.pr.step()
		soup = bs4.BeautifulSoup(html, 'lxml')
		div = soup.find('div',{'class':'fitxa'})
		dl_list = div.findAll('dl')
		#assign = {}
		for dl in dl_list:
			dt = dl.find('dt').text
			if dt == 'Desde':
				str_from_date = dl.find('dd').text
				assign['from'] = str(self.parse_assignment_date(str_from_date))
			elif dt == 'Fecha límite de entrega':
				str_to_date = dl.find('dd').text
				assign['to'] = str(self.parse_assignment_date(str_to_date))
			elif dt == 'Comentarios':
				comment = dl.find('dd').text
				assign['comment'] = comment
			elif dt == 'Adjuntos':
				li_attachments = dl.find('dd').findAll('li')
				attachments = []
				for li in li_attachments:
					a = li.find('a')
					url = 'https://raco.fib.upc.edu' + a['href']
					title = a.text.strip()
					attach = {}
					attach['url'] = url
					attach['title'] = title
					attachments.append(attach)
				assign['attachments'] = attachments
				self.pr.add(len(attachments))
		#print(assign)
		return assign

	def parse_notices(self, name, code, changelog):
		#print('Parsing subject {} with code {}'.format(name, code))
		url = 'https://raco.fib.upc.edu/avisos/llista.jsp?espai=' + code
		s = self.session
		html = s.get(url).text
		self.pr.step()
		soup = bs4.BeautifulSoup(html, 'lxml')
		ul = soup.find('ul',{'class':'avisos'})
		#print(ul)
		entries = []
		#changelog = {}
		li_list = ul.findAll('li')
		self.pr.add(len(li_list))
		for li in li_list:
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
			self.parse_notice_entry(entry)
			entries.append(entry)
		return entries
	
	def parse_notice_entry(self, entry):
		url = entry['a']
		s = self.session
		r = s.get(url)
		self.pr.step()
		html = r.text
		soup = bs4.BeautifulSoup(html, 'lxml')
		cont = soup.find('div',{'class':'dintre_contingut'})
		str_date = cont.find('span',{'class':'date'}).text

		entry['date'] = self.parse_assignment_date(str_date).strftime(FORMAT_DATE)
		descs = cont.findAll('p', recursive=False)[1:-2]
		desc = ''
		for p in descs:
			for s in p.strings:
				desc += '{}\n'.format(s)
		#print(desc)
		entry['desc'] = desc
		#print(cont)
		attachments = []
		attach = cont.find('div',{'class':'post-attachments'})
		if attach != None:
			attach_list = attach.findAll('li')
			for li in attach_list:
				attachment = {}
				a = li.find('a')
				attachment['name'] = a.text
				attachment['url'] = 'https://raco.fib.upc.edu' + a['href']
				#self.download_file(entry, attachment)
				attachments.append(attachment)
			self.pr.add(len(attachments))
		entry['attachments'] = attachments

#	def download_file(self, entry, attachment):
#		subject = entry['subject']
#		url = attachment['url']
#		filename = attachment['name']
#		#print('Downloading {}'.format(filename))
#		s = self.session
#
#		r = s.get(url)
#		tmpf = '/tmp/raco.tmp'
#
#		with open(tmpf, 'wb') as f:
#			f.write(r.content)
#
#		md5_new = md5(tmpf)
#
#		filepath = 'raco/' + subject + '/' + filename
#
#		if not os.path.exists(os.path.dirname(filepath)):
#			os.makedirs(os.path.dirname(filepath))
#		
#		if os.path.isfile(filepath):
#			md5_old = md5(filepath)
#			if md5_old != md5_new:
#				#print("New version of the file "+filepath)
#				with open(filepath, 'wb') as f:
#					f.write(r.content)
#		else:
#			#print("New file "+filepath)
#			with open(filepath, 'wb') as f:
#				f.write(r.content)

	def update_stored(self, data):
		for s in data:
			subject = data[s]
			name = subject['name']
			self.update_subject(subject)

	def update_subject(self, subject):
		# TODO Assuming that the subject has a folder
		# FIXME The README file can change
		notices = subject['notices']
		sub_title = subject['name']
		subject_dir = 'raco/' + sub_title
		for notice in notices:
			raw_title = notice['title']
			keepcharacters = (' ', '.', '_', '+', '-')
			sane_title = "".join([c for c in raw_title if c.isalnum() or c in keepcharacters]).strip()
			date = notice['date']

			#print("{}/{} {}".format(sub_title, date, sane_title))
			#dir_name = "{}".format(sane_title)
			dir_name = "{} ({})".format(sane_title, date)
			notice_dir = subject_dir + '/' + dir_name
			if not os.path.exists(notice_dir):
				os.makedirs(notice_dir)

			text = ""
			text += 'Title: {}\n'.format(raw_title)
			text += 'Date of creation: {}\n'.format(date)
			text += '\n'
			text += notice['desc']

			with open(notice_dir + '/' + 'README', 'w') as f:
				f.write(text)

			self.update_attachments(notice, notice_dir)
			t = time.mktime((time.strptime(date, '%Y-%m-%d')))
			os.utime(notice_dir, (t,t))

	def update_attachments(self, notice, notice_dir):
		for attachment in notice['attachments']:
			self.update_attachment(attachment, notice_dir)
		
			
	def update_attachment(self, attachment, attachment_dir):
		url = attachment['url']
		filename = attachment['name']
		#print('Downloading {}'.format(filename))
		filepath = attachment_dir + '/' + filename

		if not os.path.exists(attachment_dir):
			os.makedirs(attachment_dir)
		
		s = self.session
		head = s.head(url)
		seems_different = False
		if 'Content-Length' in head.headers:
			remote_size = int(head.headers['Content-Length'])
			if os.path.isfile(filepath):
				local_stat = os.stat(filepath)
				local_size = local_stat.st_size
				if remote_size == local_size:
					# Both files seem the same
					self.pr.step()
					return
				else:
					seems_different = True

		r = s.get(url)
		tmpf = '/tmp/raco.tmp'

		self.pr.step()

		with open(tmpf, 'wb') as f:
			f.write(r.content)

		md5_new = md5(tmpf)


		if os.path.isfile(filepath):
			md5_old = md5(filepath)
			if md5_old != md5_new:
				#print("New version of the file "+filepath)
				with open(filepath, 'wb') as f:
					f.write(r.content)
				self.changes.mod(filepath)
			else:
				# Same version
				if seems_different: self.raco_errors += 1
		else:
			self.changes.new(filepath)
			#print("New file "+filepath)
			with open(filepath, 'wb') as f:
				f.write(r.content)

	def update(self):
		self.login()
		self.parse()

	def status(self):
		self.search_assignments(self.data)


#with open('config.json','r') as f:
#	config = json.load(f)
#
#r = Raco(config)
#r.login()
##with open('raco.html','r') as f:
##	r.html = f.read()
#
#r.parse()
