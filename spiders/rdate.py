import datetime

def rdate(date=datetime.date.today()):
	months = ['J','F','M','A','Y','U','L','G','S','O','N','D']
	today = date
	month = months[today.month-1]
	year = str(today.year)
	day = str(today.day)
	return year+month+day
