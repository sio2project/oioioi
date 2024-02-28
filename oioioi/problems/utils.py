import mimetypes
import sys
import zipfile
from collections import defaultdict

import django
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.http import Http404, HttpResponse
from django.utils import translation
from oioioi.base.utils import request_cached
from oioioi.contests.models import ProblemInstance, Submission
from oioioi.contests.processors import recent_contests
from oioioi.contests.utils import (
    administered_contests,
    can_admin_contest,
    is_contest_admin,
    is_contest_basicadmin,
)
from oioioi.problems.models import (
    AlgorithmTagProposal,
    DifficultyTagProposal,
    ProblemStatement,
    ProblemStatistics,
    UserStatistics,
)
from oioioi.programs.models import (
    GroupReport,
    ModelProgramSubmission,
    TestReport,
    LanguageOverrideForTest,
)


@request_cached
def can_add_problems(request):
    return request.user.has_perm('problems.problems_db_admin') or is_contest_basicadmin(
        request
    )


def can_upload_problems(request):
    if not request.user.is_authenticated:
        return False
    if is_contest_admin(request):
        return True
    return can_add_to_problemset(request)


def can_admin_problem(request, problem):
    """Checks if the user can admin the given problem.

    The user can admin the given problem if at least one of the following is true:
    - the user can administer the problems database;
    - the user can administer the problem;
    - the user is the author of the problem;
    - the user can administer the contest where the problem was initially added.

    The caller should guarantee that any of the given arguments is not None.
    """
    if request.user.has_perm('problems.problems_db_admin'):
        return True
    if request.user.has_perm('problems.problem_admin', problem):
        return True
    if request.user == problem.author:
        return True
    # If a user is administering a contest where the task was initially added,
    # he is considered to be a co-author of the task, giving him rights to admin it.
    if problem.contest:
        return can_admin_contest(request.user, problem.contest)
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
    return (
        is_contest_basicadmin(request)
        and ProblemInstance.objects.filter(
            problem=problem, contest=request.contest
        ).exists()
    )


def can_admin_problem_instance(request, pi):
    if pi.contest:
        return can_admin_contest(request.user, pi.contest)
    else:
        return can_admin_problem(request, pi.problem)


@request_cached
def can_add_to_problemset(request):
    """Returns True if request.user is authenticated and:
    EVERYBODY_CAN_ADD_TO_PROBLEMSET in settings.py is set on True or
    user is a teacher or
    user is a superuser or
    user is a database admin
    """
    if not request.user.is_authenticated:
        return False
    if settings.EVERYBODY_CAN_ADD_TO_PROBLEMSET:
        return True
    if request.user.has_perm('teachers.teacher'):
        return True
    if request.user.is_superuser:
        return True
    return request.user.has_perm('problems.problems_db_admin')


def query_statement(problem_id):
    statements = ProblemStatement.objects.filter(problem=problem_id)
    if not statements:
        return None

    lang_prefs = (
        [translation.get_language()] + ['', None] + [l[0] for l in settings.LANGUAGES]
    )
    ext_prefs = ['.zip', '.pdf', '.ps', '.html', '.txt']

    def sort_key(statement):
        try:
            lang_pref = lang_prefs.index(statement.language)
        except ValueError:
            lang_pref = sys.maxsize
        try:
            ext_pref = (ext_prefs.index(statement.extension), '')
        except ValueError:
            ext_pref = (sys.maxsize, statement.extension)
        return lang_pref, ext_pref

    return sorted(statements, key=sort_key)[0]


def query_zip(statement, path):
    if statement.extension != '.zip':
        raise SuspiciousOperation

    # ZipFile will call seek(), so we need a real file here
    zip = zipfile.ZipFile(statement.content.read_using_cache())
    try:
        info = zip.getinfo(path)
    except KeyError:
        raise Http404

    content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    response = HttpResponse(zip.read(path), content_type=content_type)
    response['Content-Length'] = info.file_size
    return response


def update_tests_from_main_pi(problem_instance, source_instance=None):
    """Deletes all tests assigned to problem_instance
    and replaces them by new ones copied from source_instance,
    or - if not specified - main_problem_instance of appropiate Problem
    """
    if problem_instance == problem_instance.problem.main_problem_instance:
        return
    source_instance = source_instance or problem_instance.problem.main_problem_instance
    if problem_instance == source_instance:
        return

    for test in problem_instance.test_set.all():
        test.delete()
    for test in source_instance.test_set.all():
        test_pk = test.pk
        test.id = None
        test.pk = None
        test.problem_instance = problem_instance
        test.save()
        assiociated_overrides = LanguageOverrideForTest.objects.filter(test=test_pk)
        for override in assiociated_overrides:
            LanguageOverrideForTest.objects.create(
                test=test,
                time_limit=override.time_limit,
                memory_limit=override.memory_limit,
                language=override.language,
            )


def get_new_problem_instance(problem, contest=None):
    """Returns a deep copy of problem.main_problem_instance,
    with an independent set of test. Returned ProblemInstance
    is already saved and contains model solutions.
    """
    pi = problem.main_problem_instance
    return copy_problem_instance(pi, contest)


def copy_problem_instance(pi, contest=None):
    """Returns a deep copy of pi,
    with an independent set of test. Returned ProblemInstance
    is already saved and contains model solutions.
    """
    orig_pk = pi.pk

    pi.id = None
    pi.pk = None
    pi.short_name = None
    pi.contest = contest
    if contest is not None:
        pi.submissions_limit = contest.default_submissions_limit
    pi.round = None
    pi.save()

    orig_pi = ProblemInstance.objects.get(pk=orig_pk)
    update_tests_from_main_pi(pi, orig_pi)
    return pi


def generate_add_to_contest_metadata(request):
    """This generates all metadata needed for
    "add to contest" functionality in problemset.
    """

    administered = administered_contests(request)
    # If user doesn't own any contest we won't show the option.
    if administered:
        show_add_button = True
    else:
        show_add_button = False
    # We want to show administered recent contests, because
    # these are most likely to be picked by an user.
    rcontests = recent_contests(request)
    administered_recent_contests = None
    if rcontests:
        administered_recent_contests = [
            contest
            for contest in rcontests
            if request.user.has_perm('contests.contest_admin', contest)
        ]
    return show_add_button, administered_recent_contests


def generate_model_solutions_context(request, problem_instance):
    """Generates context dictionary for model solutions view
    for "problem_instance"'s package.
    """

    filter_kwargs = {
        'test__isnull': False,
        'submission_report__submission__problem_instance': problem_instance,
        'submission_report__submission__programsubmission'
        '__modelprogramsubmission__isnull': False,
        'submission_report__status': 'ACTIVE',
    }
    test_reports = TestReport.objects.filter(**filter_kwargs).select_related()
    filter_kwargs = {
        'submission_report__submission__problem_instance': problem_instance,
        'submission_report__submission__programsubmission'
        '__modelprogramsubmission__isnull': False,
        'submission_report__status': 'ACTIVE',
    }
    group_reports = GroupReport.objects.filter(**filter_kwargs).select_related()
    submissions = (
        ModelProgramSubmission.objects.filter(problem_instance=problem_instance)
        .order_by('model_solution__order_key')
        .select_related('model_solution')
        .all()
    )
    tests = problem_instance.test_set.order_by('order', 'group', 'name').all()

    group_results = defaultdict(lambda: defaultdict(lambda: None))
    for gr in group_reports:
        group_results[gr.group][gr.submission_report.submission_id] = gr

    test_results = defaultdict(lambda: defaultdict(lambda: None))
    for tr in test_reports:
        test_results[tr.test_id][tr.submission_report.submission_id] = tr

    submissions_percentage_statuses = {s.id: '25' for s in submissions}
    rows = []
    submissions_row = []
    for t in tests:
        row_test_results = test_results[t.id]
        row_group_results = group_results[t.group]
        percentage_statuses = {s.id: '100' for s in submissions}
        for s in submissions:
            if row_test_results[s.id] is not None:
                time_ratio = (
                    float(row_test_results[s.id].time_used)
                    / row_test_results[s.id].test_time_limit
                )
                if time_ratio <= 0.25:
                    percentage_statuses[s.id] = '25'
                elif time_ratio <= 0.50:
                    percentage_statuses[s.id] = '50'
                    if submissions_percentage_statuses[s.id] != '100':
                        submissions_percentage_statuses[s.id] = '50'
                else:
                    percentage_statuses[s.id] = '100'
                    submissions_percentage_statuses[s.id] = '100'

        rows.append(
            {
                'test': t,
                'results': [
                    {
                        'test_report': row_test_results[s.id],
                        'group_report': row_group_results[s.id],
                        'is_partial_score': s.problem_instance.controller._is_partial_score(
                            row_test_results[s.id]
                        ),
                        'percentage_status': percentage_statuses[s.id],
                    }
                    for s in submissions
                ],
            }
        )

    for s in submissions:
        status = s.status
        if s.status == 'OK' or s.status == 'INI_OK':
            status = 'OK' + submissions_percentage_statuses[s.id]

        submissions_row.append({'submission': s, 'status': status})

    total_row = {
        'test': sum(t.time_limit for t in tests),
        'results': [
            sum(t[s.id].time_used if t[s.id] else 0 for t in test_results.values())
            for s in submissions
        ],
    }

    return {
        'problem_instance': problem_instance,
        'submissions_row': submissions_row,
        'submissions': submissions,
        'rows': rows,
        'total_row': total_row,
    }


class FakeOriginInfoValue(object):
    value = None
    order = float('inf')
    cat = None

    def __init__(self, category):
        self.cat = category

    def __eq__(self, other):
        if type(other) is FakeOriginInfoValue:
            return self.cat == other.cat
        return False

    def __hash__(self):
        return hash(self.cat)


def get_prefetched_value(problem, category):
    """Returns OriginInfoValue for the given Problem and OriginInfoCategory.

    You can't filter the prefetched sets and since the OriginInfoValue set
    only has a few elements it should be faster to choose from all of them.

    If there is no OriginInfoValue for this OriginInfoCategory and Problem,
    a fake object with .value == None and .order == infinity is returned.

    Avoids database queries if and only if the problem was from a queryset on
    which `prefetch_related('origininfovalue_set__category')` was called. If
    prefetching was impossible you should just filter instead.
    """
    for oiv in problem.origininfovalue_set.all():
        if oiv.category == category:
            return oiv
    return FakeOriginInfoValue(category)


def show_proposal_form(problem, user):
    if not user.is_authenticated:
        return False

    if AlgorithmTagProposal.objects.all().filter(
        problem=problem, user=user
    ) or DifficultyTagProposal.objects.all().filter(problem=problem, user=user):
        return False

    ps = ProblemStatistics.objects.all().filter(problem=problem).first()
    us = UserStatistics.objects.all().filter(problem_statistics=ps, user=user).first()
    if not us or not us.has_solved:
        return False

    return True


def filter_my_all_visible_submissions(request, queryset):
    """Filters all solusion visible for the currently logged in user
    from the given queryset. Returns the result as a queryset.

    The filtering is not stable: the order of entries in the returned
    queryset may differ from the original.
    """

    result = Submission.objects.none()
    resolved = set()

    for submission in queryset:
        pi = submission.problem_instance

        if pi.contest and pi.contest in resolved:
            continue
        if not pi.contest and pi in resolved:
            continue

        if pi.contest:
            controller = pi.contest.controller
            current_queryset = queryset.filter(problem_instance__contest=pi.contest)
            resolved.add(pi.contest)
        else:
            controller = pi.controller
            current_queryset = queryset.filter(problem_instance=pi)
            resolved.add(pi)

        request.contest = pi.contest
        current_queryset = controller.filter_my_visible_submissions(
            request, current_queryset
        )
        result = result.union(current_queryset)

    return result
