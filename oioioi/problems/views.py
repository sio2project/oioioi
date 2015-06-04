# coding: utf-8
import urllib

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST
from django.template.response import TemplateResponse

from oioioi.base.utils import tabbed_view
from oioioi.problems.models import ProblemStatement, ProblemAttachment, \
        Problem, ProblemPackage
from oioioi.filetracker.utils import stream_file
from oioioi.problems.utils import can_admin_problem, \
        query_statement, is_problem_author, get_submission_without_contest, \
        can_see_submission_without_contest
from oioioi.problems.problem_sources import problem_sources
from oioioi.problems.problem_site import problem_site_tab_registry
from oioioi.contests.models import Submission, SubmissionReport
from oioioi.contests.utils import is_contest_admin
from oioioi.contests.middleware import activate_contest
from oioioi.contests.views import submission_view_unsafe, \
        rejudge_submission_view_unsafe, change_submission_kind_view_unsafe
# problem_site_statement_zip_view is used in one of the tabs
# in problem_site.py. We placed the view in problem_site.py
# instead of views.py to avoid circular imports. We still import
# it here to use it in urls.py.
from oioioi.problems.problem_site import problem_site_statement_zip_view


def show_statement_view(request, statement_id):
    statement = get_object_or_404(ProblemStatement, id=statement_id)
    if not can_admin_problem(request, statement.problem):
        raise PermissionDenied
    return stream_file(statement.content)


def show_problem_attachment_view(request, attachment_id):
    attachment = get_object_or_404(ProblemAttachment, id=attachment_id)
    if not can_admin_problem(request, attachment.problem):
        raise PermissionDenied
    return stream_file(attachment.content)


def _get_package(request, package_id):
    package = get_object_or_404(ProblemPackage, id=package_id)
    has_perm = False
    if package.contest:
        has_perm = request.user.has_perm('contests.contest_admin',
                package.contest)
    elif package.problem:
        has_perm = request.user.has_perm('problems.problem_admin',
                package.problem)
    if not has_perm:
        raise PermissionDenied
    return package


def download_problem_package_view(request, package_id):
    package = _get_package(request, package_id)
    return stream_file(package.package_file)


def download_package_traceback_view(request, package_id):
    package = _get_package(request, package_id)
    if not package.traceback:
        raise Http404
    return stream_file(package.traceback)


@transaction.non_atomic_requests
def add_or_update_problem_view(request):
    contest = request.contest

    if 'problem' in request.GET:
        existing_problem = \
                get_object_or_404(Problem, id=request.GET['problem'])
        if contest and not existing_problem.probleminstance_set.filter(
                contest=contest).exists():
            raise Http404
        if not can_admin_problem(request, existing_problem):
            raise PermissionDenied
    else:
        existing_problem = None
        if not request.user.has_perm('problems.problems_db_admin'):
            if not contest:
                raise PermissionDenied
            if not is_contest_admin(request):
                raise PermissionDenied

    context = {'existing_problem': existing_problem}
    tab_kwargs = {
        'contest': contest,
        'existing_problem': existing_problem
    }

    tab_link_params = request.GET.dict()

    def build_link(tab):
        tab_link_params['key'] = tab.key
        return request.path + '?' + urllib.urlencode(tab_link_params)

    return tabbed_view(request, 'problems/add_or_update.html', context,
            problem_sources(request), tab_kwargs, build_link)


def problemset_main_view(request):
    problems = Problem.objects.filter(is_public=True,
            problemsite__isnull=False)

    return TemplateResponse(request,
       'problems/problemset/problem_list.html',
      {'problems': problems,
       'page_title':
          _("Welcome to problemset, the place where all the problems are."),
       'select_problem_src': request.GET.get('select_problem_src')})


def problemset_my_problems_view(request):
    problems = Problem.objects.filter(author=request.user,
            problemsite__isnull=False)

    return TemplateResponse(request,
         'problems/problemset/problem_list.html',
         {'problems': problems,
          'page_title': _("My problems"),
          'select_problem_src': request.GET.get('select_problem_src')})


def problem_site_view(request, site_key):
    problem = get_object_or_404(Problem, problemsite__url_key=site_key)
    context = {'problem': problem,
               'select_problem_src': request.GET.get('select_problem_src')}
    tab_kwargs = {'problem': problem}

    tab_link_params = request.GET.dict()
    if 'page' in tab_link_params:
        del tab_link_params['page']

    def build_link(tab):
        tab_link_params['key'] = tab.key
        return request.path + '?' + urllib.urlencode(tab_link_params)

    return tabbed_view(request, 'problems/problemset/problem_site.html',
            context, problem_site_tab_registry, tab_kwargs, build_link)


def problem_site_external_statement_view(request, site_key):
    problem = get_object_or_404(Problem, problemsite__url_key=site_key)
    statement = query_statement(problem.id)
    if statement.extension == '.zip' \
            and not can_admin_problem(request, problem):
        raise PermissionDenied
    return stream_file(statement.content)


def problem_site_external_attachment_view(request, site_key, attachment_id):
    problem = get_object_or_404(Problem, problemsite__url_key=site_key)
    attachment = get_object_or_404(ProblemAttachment, id=attachment_id)
    if attachment.problem.id != problem.id:
        raise PermissionDenied
    return stream_file(attachment.content)


def get_report_HTML_view(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    if not can_see_submission_without_contest(request, submission):
        return HttpResponseForbidden()
    controller = submission.problem_instance.controller
    reports = ''
    queryset = SubmissionReport.objects.filter(submission=submission). \
        prefetch_related('scorereport_set')
    for report in controller.filter_visible_reports(request, submission,
            queryset.filter(status='ACTIVE')):
        reports += controller.render_report(request, report)

    if reports:
        reports = _(u"<center>Reports are not available now (ಥ ﹏ ಥ)</center>")
    return HttpResponse(reports)


def submission_without_contest_view(request, submission_id):
    submission = get_submission_without_contest(request, submission_id)
    return submission_view_unsafe(request, submission)


@require_POST
def rejudge_submission_without_contest_view(request, submission_id):
    submission = get_submission_without_contest(request, submission_id)
    rejudge_submission_view_unsafe(request, submission)
    return redirect('submission_without_contest', submission_id=submission_id)


def change_submission_kind_without_contest_view(request, submission_id, kind):
    submission = get_submission_without_contest(request, submission_id)
    change_submission_kind_view_unsafe(request, submission, kind)
    return redirect('submission_without_contest', submission_id=submission_id)
