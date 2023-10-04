import os

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.http import Http404

from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.base.utils import request_cached
from oioioi.contests.attachment_registration import (
    attachment_registry,
    attachment_registry_problemset,
)
from oioioi.contests.utils import (
    can_enter_contest,
    contest_exists,
    is_contest_admin,
    is_contest_basicadmin,
    visible_problem_instances,
)
from oioioi.contests.models import ProblemInstance
from oioioi.filetracker.utils import stream_file
from oioioi.problems.utils import can_admin_problem
from oioioi.testspackages.models import TestsPackage


@request_cached
def visible_tests_packages(request):
    problems = [pi.problem for pi in visible_problem_instances(request)]
    tests_packages = TestsPackage.objects.filter(problem__in=problems)
    return [
        tp
        for tp in tests_packages
        if tp.package is not None and (
            is_contest_basicadmin(request) or
            tp.is_visible(request.timestamp)
        )
    ]


@attachment_registry.register
def get_tests(request):
    tests = []
    for tp in visible_tests_packages(request):
        t = {
            'category': tp.problem,
            'name': os.path.basename(tp.name) + '.zip',
            'description': tp.description,
            'link': reverse(
                'test', kwargs={'contest_id': request.contest.id, 'package_id': tp.id}
            ),
            'pub_date': tp.publish_date,
        }
        tests.append(t)
    return tests


@attachment_registry_problemset.register
def get_tests_for_problem(request, problem):
    tests = []
    if can_admin_problem(request, problem):
        tests_packages = TestsPackage.objects.filter(problem=problem)
        for tp in tests_packages:
            t = {
                'category': tp.problem,
                'name': os.path.basename(tp.name) + '.zip',
                'description': tp.description,
                'link': reverse('test_for_problem', kwargs={'package_id': tp.id}),
                'pub_date': tp.publish_date,
            }
            tests.append(t)
    return tests


def get_tests_package_file(test_package):
    file_name = '%s.zip' % test_package.name
    return stream_file(test_package.package, name=file_name)


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
def test_view(request, package_id):
    tp = get_object_or_404(TestsPackage, id=package_id)
    # Check if TestPackage is attached to requested contest
    if not ProblemInstance.objects.filter(
        problem=tp.problem, contest=request.contest
    ).exists():
        raise Http404
    if not is_contest_admin(request) and not tp.is_visible(request.timestamp):
        raise PermissionDenied
    return get_tests_package_file(tp)


@enforce_condition(not_anonymous)
def test_view_for_problem(request, package_id):
    tp = get_object_or_404(TestsPackage, id=package_id)
    if not can_admin_problem(request, tp.problem):
        raise PermissionDenied
    return get_tests_package_file(tp)
