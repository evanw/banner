# Banner.py
This is a Python scraper for [Banner](http://boca.brown.edu), which is Brown University's course catalog and registration system. It parses data from both the catalog and the schedule into Python objects, which can then be serialized to XML or JSON with the provided convenience functions.

## Quick start
If you just want the data, copy and paste this into your Python interpreter:

    class Course:
        def __init__(self):
            self.name = ''
            self.title = ''
            self.attributes = ''
            self.description = ''
            self.semesters = [] # list of Semester objects

    class Semester:
        def __init__(self):
            self.name = ''
            self.exam_time = ''
            self.exam_date = ''
            self.sections = [] # list of Section objects

    class Section:
        def __init__(self):
            self.crn = 0
            self.levels = ''
            self.xlist_data = ''
            self.registration_dates = ''
            self.meetings = [] # list of Meeting objects

    class Meeting:
        def __init__(self):
            self.type = ''
            self.days = ''
            self.time = ''
            self.where = ''
            self.date_range = ''
            self.instructors = ''

    import pickle, urllib
    url = 'https://github.com/downloads/evanw/banner/banner.pickle'
    courses = pickle.loads(urllib.urlopen(url).read())

This contains the course information for Fall 2011 and Spring 2012 and can also be downloaded as [XML](https://github.com/downloads/evanw/banner/banner.xml) or [JSON](https://github.com/downloads/evanw/banner/banner.json).

## Dependencies
* Beautiful Soup: [http://www.crummy.com/software/BeautifulSoup/](http://www.crummy.com/software/BeautifulSoup/) (included)
* Mechanize: [http://wwwsearch.sourceforge.net/mechanize/](http://www.crummy.com/software/BeautifulSoup/) (not included)

## Usage

Since downloading is such a time-consuming operation, downloading and parsing are done in two different steps:

    import banner
    semester = 'Fall 2011'

    # download all pages for Fall 2011 into a folder named .cache
    banner.download_semester(semester)

    # scrape all the previously downloaded pages in the .cache folder
    courses = banner.parse_semester(semester)

See `gen_quick_downloads.py` for a more complex example involving multiple semesters.
