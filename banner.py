from BeautifulSoup import BeautifulSoup, NavigableString, Tag
import mechanize
import os
import re

'''
Takes two semester strings as arguments and behave like the python cmp()
function. Semester strings start with Spring, Summer, Fall, or Winter and end
with a year (for example, "Fall 2010"). The cmp(a, b) function returns a
negative value if a comes before b, zero if a == b, and a positive value if a
comes after b.
'''
def compare_semesters(a_name, b_name):
	seasons = { 'Spring': 0, 'Summer': 1, 'Fall': 2, 'Winter': 3 }
	a_season, a_year = a_name.split()
	b_season, b_year = b_name.split()
	year_cmp = int(a_year).__cmp__(int(b_year))
	season_cmp = seasons[a_season].__cmp__(seasons[b_season])
	return year_cmp if year_cmp else season_cmp

################################################################################
# class structure
################################################################################

'''
Banner is represented as a list of Course objects, which own Semester objects.
'''
class Course:
	def __init__(self):
		self.name = ''
		self.title = ''
		self.attributes = ''
		self.description = ''
		self.semesters = []

	'''
	Returns the semester with the given name, creating it first if needed.
	'''
	def get_semester(self, name):
		for semester in self.semesters:
			if semester.name == name:
				return semester
		semester = Semester()
		semester.name = name
		self.semesters.append(semester)
		return semester

'''
Semester objects own Section objects and are owned by Course objects.
'''
class Semester:
	def __init__(self):
		self.name = ''
		self.exam_time = ''
		self.exam_date = ''
		self.sections = []

'''
Section objects own Meeting objects and are owned by Semester objects.
'''
class Section:
	def __init__(self):
		self.crn = 0
		self.levels = ''
		self.xlist_data = ''
		self.registration_dates = ''
		self.meetings = []

'''
Meeting objects are owned by Section objects.
'''
class Meeting:
	def __init__(self):
		self.type = ''
		self.days = ''
		self.time = ''
		self.where = ''
		self.date_range = ''
		self.instructors = ''

################################################################################
# xml output
################################################################################

def _courses_to_xml_helper(doc, parent, obj, name):
	element = doc.createElement(name)
	parent.appendChild(element)
	if isinstance(obj, int) or isinstance(obj, float):
		obj = str(obj)
	if isinstance(obj, basestring):
		element.appendChild(doc.createTextNode(obj))
	elif isinstance(obj, list):
		for x in obj:
			_courses_to_xml_helper(doc, element, x, x.__class__.__name__.lower())
	else:
		for x in obj.__dict__:
			_courses_to_xml_helper(doc, element, obj.__dict__[x], x)

'''
Takes an array of Course objects and returns an XML string.
'''
def courses_to_xml(courses):
	import xml.dom.minidom as xml
	doc = xml.Document()
	_courses_to_xml_helper(doc, doc, courses, 'courses')
	return doc.toxml()

################################################################################
# json output
################################################################################

def _courses_to_json_helper(obj):
	if isinstance(obj, int) or isinstance(obj, float) or isinstance(obj, basestring):
		return obj
	elif isinstance(obj, list):
		return [_courses_to_json_helper(x) for x in obj]
	else:
		return dict((x, _courses_to_json_helper(obj.__dict__[x])) for x in obj.__dict__)

'''
Takes an array of Course objects and returns a JSON string.
'''
def courses_to_json(courses):
	import json
	return json.dumps(_courses_to_json_helper(courses))

################################################################################
# downloading
################################################################################

CACHE_DIR = '.cache'
BASE_URL = 'https://selfservice.brown.edu'

SCHEDULE_MAIN_URL = BASE_URL + '/ss/bwckschd.p_disp_dyn_sched'
SCHEDULE_DETAIL_URL = '/ss/bwckschd.p_disp_detail_sched'
SCHEDULE_LINK_REGEX = r'^/ss/bwckschd\.p_disp_detail_sched'
SCHEDULE_DATA_PATH = CACHE_DIR + '/%s/schedule/'

CATALOG_MAIN_URL = BASE_URL + '/ss/bwckctlg.p_disp_dyn_ctlg'
CATALOG_DETAIL_URL = '/ss/bwckctlg.p_display_courses'
CATALOG_LINK_REGEX = r'^/ss/bwckctlg\.p_disp_course_detail'
CATALOG_DATA_PATH = CACHE_DIR + '/%s/catalog/'

EXAM_LINK_REGEX = r'.*Display_Exam'
EXAM_DATA_PATH = CACHE_DIR + '/%s/exam times/'
BAD_EXAM_INFO = 'Only the Primary Meeting of a course has scheduled exam information'

'''
Saves data in the given path after creating directories as needed.
'''
def _save(path, data):
	try:
		os.makedirs(path[:path.rfind('/')])
	except OSError:
		pass
	open(path, 'w').write(data)

def _download_semester_helper(semester, start_url, path_template):
	# open the main schedule page
	b = mechanize.Browser()
	b.set_handle_robots(False)
	b.open(start_url)

	# select the <option> that starts with the text in semester variable
	b.select_form(nr=0)
	for item in b.find_control(type='select').items:
		if item.get_labels()[0].text.startswith(semester):
			item.selected = True
			break
	b.submit()

	# get the list of department codes
	b.select_form(nr=0)
	department_codes = map(str, b.find_control(type='select', nr=0).items)

	# download each department schedule
	for i, department_code in enumerate(department_codes):
		b.select_form(nr=0)
		b.find_control(type='select', nr=0).get(department_code).selected = True
		b.submit()
		html = b.response().read()
		_save((path_template % semester) + department_code + '.html', html)
		b.back()
		print 'downloaded department %s, %.2f%% done' % (department_code,
			100.0 * (i + 1) / len(department_codes))

def _download_exam_times(semester):
	directory = SCHEDULE_DATA_PATH % semester
	filenames = os.listdir(directory)

	for i, filename in enumerate(filenames):
		if not filename.endswith('.html'):
			continue

		data = open(directory + filename).read()
		soup = BeautifulSoup(data)
		for link in soup.findAll(href=re.compile(SCHEDULE_LINK_REGEX)):
			title, crn, name, index = link.text.rsplit('-', 3)
			href = BASE_URL + link['href']

			b = mechanize.Browser()
			b.set_handle_robots(False)
			b.open(href)

			name = name.strip()
			for link in b.links(url_regex=re.compile(EXAM_LINK_REGEX)):
				b.follow_link(link)
				html = b.response().read()
				b.back()
				if 'Exam Date' in html and 'Exam Time' in html:
					_save((EXAM_DATA_PATH % semester) + name + '.html', html)
					print 'saved exam time for %s' % name
					break

		print 'parsed %s, %.2f%% done' % (filename, 100.0 * (i + 1) / len(filenames))

'''
Download the entire semester given by the semester name (example: "Fall 2010")
and store it in the local cache directory.
'''
def download_semester(semester_name):
	print 'downloading', semester_name

	print 'downloading schedule'
	_download_semester_helper(semester_name, SCHEDULE_MAIN_URL, SCHEDULE_DATA_PATH)

	print 'downloading catalog'
	_download_semester_helper(semester_name, CATALOG_MAIN_URL, CATALOG_DATA_PATH)

	print 'downloading exam times'
	_download_exam_times(semester_name)

################################################################################
# parsing
################################################################################

# get the text in between the nodes
def to_str(element):
	return ''.join(element.findAll(text=True)).replace('&nbsp;', ' ').strip()

# get the text in between the nodes, but also convert <br> to '\n'
def to_str_br(element):
	if not len(element.contents):
		return ''
	stopNode = element._lastRecursiveChild().next
	strings = []
	current = element.contents[0]
	while current is not stopNode:
		if isinstance(current, NavigableString):
			strings.append(current)
		elif isinstance(current, Tag) and current.name.lower() == 'br':
			strings.append('\n')
		current = current.next
	return ''.join(strings).replace('&nbsp;', ' ').strip()

# normalize whitespace
def fix(text):
	return re.sub(' +', ' ', text.strip())

def _parse_semester_schedule(semester_name):
	directory = SCHEDULE_DATA_PATH % semester_name
	filenames = os.listdir(directory)
	name_to_course = {}

	for i, filename in enumerate(filenames):
		if not filename.endswith('.html'):
			continue

		data = open(directory + filename).read()
		soup = BeautifulSoup(data)
		for link in soup.findAll(href=re.compile(SCHEDULE_LINK_REGEX)):
			# <table>
			#   <tr><th><a>this link</a></th></tr>
			#   <tr><td>the goods</td></tr>
			# </table>
			# a -> th -> tr -> tr -> td
			element = link.parent.parent.nextSibling.nextSibling

			# extract section information from the link
			section = Section()
			title, crn, name, index = link.text.rsplit('-', 3)
			section.crn = int(fix(crn))

			# extract section information from the details
			lines = to_str(element).split('\n')
			items = {}
			for line in lines:
				if ':' in line:
					key, value = line.split(':', 1)
					items[key] = value.strip()
			section.levels = fix(items.get('Levels', ''))
			section.registration_dates = fix(items.get('Registration Dates', ''))

			# special-case crosslist data
			xlist_data = to_str_br(element)
			if 'XLIST' in name and 'Associated Term:' in xlist_data:
				section.xlist_data = xlist_data[:xlist_data.find('Associated Term:')].replace('&nbsp;', ' ').strip()

			# extract meetings (xlists don't have tables)
			table = element.find('table')
			section.meetings = []
			if table:
				rows = table.findAll('tr')
				labels = [fix(to_str(cell).lower()).replace(' ', '_') for cell in rows[0].findAll('th')]
				for row in rows[1:]:
					cells = [fix(to_str(cell)) for cell in row.findAll('td')]
					meeting_dict = dict(zip(labels, cells))
					meeting = Meeting()
					meeting.type = meeting_dict['type']
					meeting.days = meeting_dict['days']
					meeting.time = meeting_dict['time']
					meeting.where = meeting_dict['where']
					meeting.date_range = meeting_dict['date_range']
					meeting.instructors = meeting_dict['instructors']
					section.meetings.append(meeting)

			# add section to courses, creating a course if necessary
			name = fix(name)
			title = fix(title)
			course = name_to_course.setdefault(name, Course())
			if course.title and course.title != title:
				print 'warning(%s): title "%s" and "%s" differ' % (name, course.title, title)
			course.name = name
			course.title = title
			course.get_semester(semester_name).sections.append(section)
		print 'parsed schedule %s, %.2f%% done' % (filename, 100.0 * (i + 1) / len(filenames))
	return name_to_course.values()

def _parse_semester_catalog(semester_name):
	directory = CATALOG_DATA_PATH % semester_name
	filenames = os.listdir(directory)
	courses = []

	for i, filename in enumerate(filenames):
		if not filename.endswith('.html'):
			continue

		data = open(directory + filename).read()
		soup = BeautifulSoup(data)
		for link in soup.findAll(href=re.compile(CATALOG_LINK_REGEX)):
			# <table>
			#   <tr><td><a>this link</a></td></tr>
			#   <tr><td>the goods</td></tr>
			# </table>
			# a -> td -> tr -> tr -> td
			element = link.parent.parent.nextSibling.nextSibling

			# extract course information from the link
			course = Course()
			name, title = link.text.split('-', 1)
			course.name = fix(name)
			course.title = fix(title)

			# extract course information from the details
			lines = to_str(element).split('\n')
			description = ''
			reading_description = True
			for line in lines:
				line = fix(line)
				if line.endswith('Credit hours') or line.endswith('Lecture hours'):
					reading_description = False
				elif line.startswith('Course Attributes:'):
					course.attributes = fix(line[line.find(':')+1:])
				elif reading_description:
					description += line + '\n'
			course.description = fix(description)

			courses.append(course)
		print 'parsed catalog %s, %.2f%% done' % (filename, 100.0 * (i + 1) / len(filenames))
	return courses

def _parse_exam_times(semester_name):
	directory = EXAM_DATA_PATH % semester_name
	filenames = os.listdir(directory)
	courses = []

	for i, filename in enumerate(filenames):
		if not filename.endswith('.html'):
			continue

		data = open(directory + filename).read()
		exam_time = None
		exam_date = None
		soup = BeautifulSoup(data)
		for element in soup.findAll(text='Exam Date'):
			exam_date = element.parent.nextSibling.nextSibling.text
		for element in soup.findAll(text='Exam Time'):
			exam_time = element.parent.nextSibling.nextSibling.text
		if exam_date and exam_time:
			course = Course()
			course.name = filename.replace('.html', '')
			courses.append(course)
			semester = course.get_semester(semester_name)
			semester.exam_date = exam_date
			semester.exam_time = exam_time

		print 'parsed exam time %s, %.2f%% done' % (filename, 100.0 * (i + 1) / len(filenames))
	return courses

'''
Parse the entire semester given by the semester name (example: "Fall 2010")
and return a list of Course objects for that semester.
'''
def parse_semester(semester_name):
	print 'parsing semester', semester_name
	schedule_courses = _parse_semester_schedule(semester_name)
	catalog_courses = _parse_semester_catalog(semester_name)
	exam_time_courses = _parse_exam_times(semester_name)

	# make indices for quick access
	schedule_index = dict((course.name, course) for course in schedule_courses)
	catalog_index = dict((course.name, course) for course in catalog_courses)
	exam_time_index = dict((course.name, course) for course in exam_time_courses)
	
	# consistency check
	for name in schedule_index:
		if name not in catalog_index:
			print 'warning(%s): course in schedule but not in catalog' % name
	for name in exam_time_index:
		if name not in catalog_index:
			print 'warning(%s): course in exam times but not in catalog' % name
	
	# merge the courses
	courses = []
	for name in catalog_index:
		course = catalog_index[name]
		courses.append(course)

		# merge with schedule
		if name in schedule_index:
			schedule_course = schedule_index[name]
			course.semesters = schedule_course.semesters

			if course.title != schedule_course.title:
				print 'warning(%s): title mismatch between catalog "%s" and schedule "%s", keeping catalog title' % \
					(name, course.title, schedule_course.title)

		# merge with exam times
		if name in exam_time_index:
			exam_time_semester = exam_time_index[name].get_semester(semester_name)
			semester = course.get_semester(semester_name)
			semester.exam_time = exam_time_semester.exam_time
			semester.exam_date = exam_time_semester.exam_date

	return courses

################################################################################
# merging
################################################################################

def merge_courses(old_courses, new_courses):
	courses_index = {}
	old_courses_index = dict((course.name, course) for course in old_courses)
	new_courses_index = dict((course.name, course) for course in new_courses)

	courses_index = old_courses_index
	for name in new_courses_index:
		new_course = new_courses_index[name]
		if name not in courses_index:
			courses_index[name] = new_course
		else:
			old_course = courses_index[name]
			old_course.semesters.extend(new_course.semesters)

			if old_course.title != new_course.title:
				print 'warning(%s): title "%s" differs from title "%s", using more recent one' % \
					(name, old_course.title, new_course.title)

			if old_course.attributes != new_course.attributes:
				print 'warning(%s): attributes "%s" differ from attributes "%s", using more recent one' % \
					(name, old_course.attributes, new_course.attributes)

			if old_course.description != new_course.description:
				print 'warning(%s): description "%s" differs from description "%s", using more recent one' % \
					(name, old_course.description, new_course.description)

			# for conflicts, use more recent info (assuming old_course is older than new_course)
			old_course.title = new_course.title
			old_course.attributes = new_course.attributes
			old_course.title = new_course.title

	return courses_index.values()

################################################################################
# unit tests
################################################################################

import unittest

class Tester(unittest.TestCase):
	def test_semester_cmp(self):
		a, b = 'Spring 2009', 'Spring 2010'
		self.assertTrue(compare_semesters(a, b) < 0 and compare_semesters(b, a) > 0)
		a, b = 'Spring 2010', 'Summer 2010'
		self.assertTrue(compare_semesters(a, b) < 0 and compare_semesters(b, a) > 0)
		a, b = 'Summer 2010', 'Fall 2010'
		self.assertTrue(compare_semesters(a, b) < 0 and compare_semesters(b, a) > 0)
		a, b = 'Fall 2010', 'Winter 2010'
		self.assertTrue(compare_semesters(a, b) < 0 and compare_semesters(b, a) > 0)
		a, b = 'Spring 2010', 'Winter 2010'
		self.assertTrue(compare_semesters(a, b) < 0 and compare_semesters(b, a) > 0)
		a, b = 'Spring 2010', 'Spring 2010'
		self.assertTrue(compare_semesters(a, b) == 0)

if __name__ == '__main__':
	import sys
	if 'test' in sys.argv:
		sys.argv.remove('test')
		unittest.main()
