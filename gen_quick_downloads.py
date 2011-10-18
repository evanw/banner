import banner
import pickle

################################################################################
# using banner library
################################################################################

semesters = ['Fall 2011', 'Spring 2012']

def path_for_semester(semester):
    return '.cache/%s/courses.pickle' % semester

def download_semesters(semesters):
    for semester in semesters:
        banner.download_semester(semester)

def parse_and_save_semesters(semesters):
    for semester in semesters:
        courses = banner.parse_semester(semester)
        open(path_for_semester(semester), 'w').write(pickle.dumps(courses))

def merge_semesters(semesters):
    courses = []
    for semester in sorted(semesters, banner.compare_semesters):
        new_courses = pickle.loads(open(path_for_semester(semester)).read())
        courses = banner.merge_courses(courses, new_courses)
    return courses

def gen_quick_downloads():
    download_semesters(semesters)
    parse_and_save_semesters(semesters)
    courses = merge_semesters(semesters)
    open('banner.xml', 'w').write(banner.courses_to_xml(courses).encode('utf8'))
    open('banner.json', 'w').write(banner.courses_to_json(courses).encode('utf8'))
    open('banner.pickle', 'w').write(courses_to_pickle(courses))

def courses_to_pickle(courses):
    # for the pickle to not depend on importing banner.py, we need to mirror the
    # class hierarchy (since otherwise we would be pickling banner.Course objects)
    class Course: pass
    class Semester: pass
    class Section: pass
    class Meeting: pass

    def conversion_helper(obj):
        if isinstance(obj, int) or isinstance(obj, float) or isinstance(obj, basestring):
            return obj
        elif isinstance(obj, list):
            return [conversion_helper(x) for x in obj]
        else:
            if isinstance(obj, banner.Course): new_obj = Course()
            elif isinstance(obj, banner.Semester): new_obj = Semester()
            elif isinstance(obj, banner.Section): new_obj = Section()
            elif isinstance(obj, banner.Meeting): new_obj = Meeting()
            else: raise Exception('attempt to pickle object of type %s' % obj.__class__.__name__)
            new_obj.__dict__ = dict((x, conversion_helper(obj.__dict__[x])) for x in obj.__dict__)
            return new_obj

    return pickle.dumps(conversion_helper(courses))

if __name__ == '__main__':
    gen_quick_downloads()
