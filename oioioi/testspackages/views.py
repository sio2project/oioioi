import os

from django.conf import settings
from django.template.response import TemplateResponse
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import not_anonymous, enforce_condition
from oioioi.contests.models import ProblemInstance
from oioioi.contests.utils import can_enter_contest, contest_exists, \
        is_contest_admin
from oioioi.filetracker.utils import stream_file
from oioioi.testspackages.models import TestsPackage
from oioioi.base.permissions import make_request_condition
from oioioi.problems.models import Problem


@make_request_condition
def is_any_tests_package_visible(request):
    pis = ProblemInstance.objects.filter(contest=request.contest)
    for pi in pis:
        try:
            problem = pi.problem
        except Problem.DoesNotExist:
            continue
        tests_packages = TestsPackage.objects.filter(problem=problem)
        for tp in tests_packages:
            if tp.is_visible(request.timestamp) and tp.package is not None:
                return True
    return False


@menu_registry.register_decorator(_("Tests"), lambda request:
        reverse('tests', kwargs={'contest_id': request.contest.id}),
        order=350)
@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(is_any_tests_package_visible)
def tests_view(request, contest_id):
    pis = ProblemInstance.objects.filter(contest=contest_id)
    tests = []
    for pi in pis:
        problem = pi.problem
        tests_packages = TestsPackage.objects.filter(problem=problem)
        round = pi.round
        for tp in tests_packages:
            if tp.is_visible(request.timestamp) and tp.package is not None:
                t = {'name': os.path.basename(tp.name) + '.zip',
                     'link': reverse('test', kwargs={'contest_id': contest_id,
                         'package_id': tp.id}),
                     'round': round,
                     'description': tp.description}
                tests.append(t)
    return TemplateResponse(request, 'testspackages/tests.html',
            {'tests': tests,
             'tests_on_page': getattr(settings, 'SUBMISSIONS_ON_PAGE', 100)})


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
def test_view(request, contest_id, package_id):
    tp = get_object_or_404(TestsPackage, id=package_id)
    if not is_contest_admin(request) and not tp.is_visible(request.timestamp):
        raise PermissionDenied
    file_name = '%s.zip' % tp.name
    file_name = file_name.encode('utf-8')
    return stream_file(tp.package, name=file_name)
