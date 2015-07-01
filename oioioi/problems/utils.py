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
from oioioi.contests.models import Submission, ProblemInstance
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


def can_admin_problem_instance(request, problem):
    """Checks if user has admin permission in ProblemInstace of given problem.
       If request.contest is not None ProblemInstace from this contest
       is taken into account, problem.main_problem_instance otherwise.

       If there is no ProblemInstace of problem in request.contest function
       returns False

       If request.user has permission to admin problem function will always
       return True.
    """
    if can_admin_problem(request, problem):
        return True
    return is_contest_admin(request) and ProblemInstance.objects \
        .filter(problem=problem, contest=request.contest).exists()


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


def can_see_submission_without_contest(request, submission):
    return submission.user == request.user or \
            can_admin_problem(request, submission.problem_instance.problem)


def get_submission_without_contest(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id) \
            .programsubmission
    assert submission.problem_instance.contest is None
    if not can_see_submission_without_contest(request, submission):
        raise Http404
    return submission


def get_submission_source_file_without_contest_or_error(request,
                                                        submission_id):
    submission = get_object_or_404(Submission, id=submission_id) \
            .programsubmission
    assert submission.problem_instance.contest is None
    controller = submission.problem_instance.controller
    if not controller.can_see_source(request, submission):
        raise PermissionDenied
    return submission.source_file


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
