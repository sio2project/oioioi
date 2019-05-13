import sys
from collections import namedtuple
from operator import itemgetter  # pylint: disable=E0611

from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from oioioi.base.menu import OrderedRegistry
from oioioi.contests.controllers import submission_template_context
from oioioi.contests.forms import SubmissionFormForProblemInstance
from oioioi.contests.models import Submission
from oioioi.problems.models import Problem, ProblemAttachment, ProblemPackage
from oioioi.problems.utils import (query_statement, query_zip, generate_add_to_contest_metadata,
                                   generate_model_solutions_context, can_admin_problem)

problem_site_tab_registry = OrderedRegistry()


def problem_site_tab(title, key, order=sys.maxsize, condition=None):
    """A decorator that for each decorated function adds a corresponding
       tab to the global problem site that uses the function to generate
       its contents.

       The decorated function should be somewhat similar to a view.
       It should take as its arguments a request and a problem, and return
       either a HttpResponseRedirect, a TemplateResponse or rendered html.

       :param title: the tab's title, will be shown on the site
       :param key: will be used as a GET parameter to indicate the active tab
       :param order: value determining the order of tabs
       :param condition: a function receiving a request and returning
           if the tab should be accessible for this request
    """

    Tab = namedtuple('Tab', ['view', 'title', 'key', 'condition'])

    if condition is None:
        condition = lambda request: True

    def decorator(func):
        problem_site_tab_registry.register(
                Tab(func, title, key, condition), order)
        return func
    return decorator


def problem_site_statement_zip_view(request, site_key, path):
    problem = get_object_or_404(Problem, problemsite__url_key=site_key)
    statement = query_statement(problem.id)
    return query_zip(statement, path)


@problem_site_tab(_("Problem statement"),
        key='statement', order=100)
def problem_site_statement(request, problem):
    statement = query_statement(problem.id)
    if not statement:
        statement_html = render_to_string(
                'problems/no-problem-statement.html',
                {'problem': problem})
    elif statement.extension == '.zip':
        response = problem_site_statement_zip_view(request,
                problem.problemsite.url_key, 'index.html')
        statement_html = mark_safe(response.content)
    else:
        statement_url = reverse('problem_site_external_statement',
                kwargs={'site_key': problem.problemsite.url_key})
        statement_html = render_to_string(
                'problems/external-statement.html',
                {'problem': problem, 'statement_url': statement_url})

    return statement_html


@problem_site_tab(_("Files"), key='files', order=200)
def problem_site_files(request, problem):
    files_qs = ProblemAttachment.objects.filter(problem=problem.id)
    files = sorted([{'name': f.filename,
                     'description': f.description,
                     'link': reverse('problem_site_external_attachment',
                         kwargs={'site_key': problem.problemsite.url_key,
                                 'attachment_id': f.id})}
                    for f in files_qs], key=itemgetter('name'))

    return TemplateResponse(request, 'problems/files.html',
        {'files': files,
         'files_on_page': getattr(settings, 'FILES_ON_PAGE', 100),
         'add_category_field': False})


@problem_site_tab(_("Submissions"), key='submissions', order=300,
        condition=lambda request: not request.contest)
def problem_site_submissions(request, problem):
    controller = problem.main_problem_instance.controller
    if request.user.is_authenticated:
        qs = controller.filter_my_visible_submissions(request,
            Submission.objects
                .filter(problem_instance=problem.main_problem_instance)
                .order_by('-date'))
    else:
        qs = []

    submissions = [submission_template_context(request, s) for s in qs]
    show_scores = any(s['can_see_score'] for s in submissions)

    return TemplateResponse(request, 'problems/submissions.html',
        {'submissions': submissions,
         'submissions_on_page': getattr(settings, 'SUBMISSIONS_ON_PAGE', 100),
         'show_scores': show_scores,
         'inside_problem_view': True})


@problem_site_tab(_("Submit"), key='submit', order=400,
        condition=lambda request: not request.contest)
def problem_site_submit(request, problem):
    if request.method == 'POST':
        form = SubmissionFormForProblemInstance(request,
                problem.main_problem_instance, request.POST, request.FILES)
        if form.is_valid():
            problem.main_problem_instance.controller.create_submission(request,
                       problem.main_problem_instance, form.cleaned_data)
            url = reverse('problem_site',
                    kwargs={'site_key': problem.problemsite.url_key})
            return redirect(url + '?key=submissions')
    else:
        form = SubmissionFormForProblemInstance(request,
                problem.main_problem_instance)
    return TemplateResponse(request, 'problems/submit.html',
            {'problem': problem, 'form': form})


@problem_site_tab(_("Secret key"), key='secret_key', order=500)
def problem_site_secret_key(request, problem):
    return TemplateResponse(request, 'problems/secret-key.html',
        {'site_key': problem.problemsite.url_key})


@problem_site_tab(_("Settings"), key='settings', order=600)
def problem_site_settings(request, problem):
    show_add_button, administered_recent_contests = generate_add_to_contest_metadata(request)
    package = ProblemPackage.objects.filter(problem=problem).first()
    model_solutions = generate_model_solutions_context(request, problem.main_problem_instance_id)
    extra_actions = problem.controller.get_extra_problem_site_actions(problem)
    return TemplateResponse(request, 'problems/settings.html',
                            {'site_key': problem.problemsite.url_key,
                             'problem': problem, 'administered_recent_contests': administered_recent_contests,
                             'package': package if package and package.package_file else None,
                             'model_solutions': model_solutions,
                             'can_admin_problem': can_admin_problem(request, problem),
                             'extra_actions': extra_actions})


@problem_site_tab(_('Add to contest'), key='add_to_contest', order=700)
def problem_site_add_to_contest(request, problem):
    return TemplateResponse(request, 'problems/add-to-contest-redirect.html',
                            {'site_key': problem.problemsite.url_key,
                             'problem': problem})
