import mimetypes
import sys
import zipfile

from django.conf import settings
from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import translation

from oioioi.base.utils import request_cached
from oioioi.contests.utils import is_contest_admin
from oioioi.contests.models import ProblemInstance
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
    if request.user == problem.author:
        return True
    if problem.contest:
        return request.user.has_perm('contests.contest_admin', problem.contest)
    return False


def can_admin_instance_of_problem(request, problem):
    """Checks if the user has admin permission in a ProblemInstace
       of the given Problem.
       If request.contest is not None then ProblemInstaces from this contest
       are taken into account, problem.main_problem_instance otherwise.

       If there is no ProblemInstace of problem in request.contest then
       the function returns False.

       If the user has permission to admin problem then the function
       will always return True.
    """
    if can_admin_problem(request, problem):
        return True
    return is_contest_admin(request) and ProblemInstance.objects \
        .filter(problem=problem, contest=request.contest).exists()


def can_admin_problem_instance(request, pi):
    if pi.contest:
        return request.user.has_perm('contests.contest_admin', pi.contest)
    else:
        return can_admin_problem(request, pi.problem)


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


def update_tests_from_main_pi(problem_instance):
    """Deletes all tests assigned to problem_instance
        and replaces them by new ones copied from
        main_problem_instance of appropiate Problem
    """
    if problem_instance == problem_instance.problem.main_problem_instance:
        return
    for test in problem_instance.test_set.all():
        test.delete()
    for test in problem_instance.problem.main_problem_instance.test_set.all():
        test.id = None
        test.pk = None
        test.problem_instance = problem_instance
        test.save()


def get_new_problem_instance(problem):
    """Returns a deep copy of problem.main_problem_instance,
        with an independent set of test. Returned ProblemInstance
        is already saved and contains model solutions copied
    """
    pi = problem.main_problem_instance
    pi.id = None
    pi.pk = None
    pi.short_name = None
    pi.save()
    update_tests_from_main_pi(pi)
    return pi
