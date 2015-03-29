import mimetypes
import sys
import zipfile

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.http import Http404, HttpResponse
from django.utils import translation

from oioioi.base.utils import request_cached
from oioioi.contests.utils import is_contest_admin
from oioioi.problems.models import ProblemStatement


@request_cached
def can_add_problems(request):
    return request.user.has_perm('problems.problems_db_admin') \
            or is_contest_admin(request)


def can_admin_problem(request, problem):
    if request.user.has_perm('problems.problems_db_admin'):
        return True
    if request.user.has_perm('problems.problem_admin', problem):
        return True
    if problem.contest:
        return request.user.has_perm('contests.contest_admin', problem.contest)
    elif problem.probleminstance_set:
        for i in problem.probleminstance_set.all():
            if request.user.has_perm('contests.contest_admin', i.contest):
                return True
    return False


def query_statement(problem_id):
    statements = ProblemStatement.objects.filter(problem=problem_id)
    if not statements:
        return None

    lang_prefs = [translation.get_language()] + ['', None] + \
            [l[0] for l in settings.LANGUAGES]
    ext_prefs = ['.zip', '.pdf', '.ps', '.html', '.txt']

    def sort_key(statement):
        try:
            lang_pref = lang_prefs.index(statement.language)
        except ValueError:
            lang_pref = sys.maxint
        try:
            ext_pref = (ext_prefs.index(statement.extension), '')
        except ValueError:
            ext_pref = (sys.maxint, statement.extension)
        return lang_pref, ext_pref

    return sorted(statements, key=sort_key)[0]


def query_zip(statement, path):
    if statement.extension != '.zip':
        raise SuspiciousOperation

    zip = zipfile.ZipFile(statement.content)
    try:
        info = zip.getinfo(path)
    except KeyError:
        raise Http404

    content_type = mimetypes.guess_type(path)[0] or \
        'application/octet-stream'
    response = HttpResponse(zip.read(path), content_type=content_type)
    response['Content-Length'] = info.file_size
    return response
