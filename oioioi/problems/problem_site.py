import sys
from collections import namedtuple
from operator import itemgetter

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404

from oioioi.base.menu import OrderedRegistry
from oioioi.problems.utils import query_statement, query_zip
from oioioi.problems.models import ProblemAttachment, Problem
from oioioi.contests.models import Submission, ProblemInstance


problem_site_tab_registry = OrderedRegistry()


def problem_site_tab(title, key, order=sys.maxint):
    """A decorator that for each decorated function adds a corresponding
       tab to the global problem site that uses the function to generate
       its contents.

       The decorated function should be somewhat similar to a view.
       It should take as its arguments a request and a problem, and return
       either a HttpResponseRedirect, a TemplateResponse or rendered html.

       :param title: the tab's title, will be shown on the site
       :param key: will be used as a GET parameter to indicate the active tab
       :order: value determining the order of tabs
    """

    Tab = namedtuple('Tab', ['view', 'title', 'key'])

    def decorator(func):
        problem_site_tab_registry.register(Tab(func, title, key), order)
        return func
    return decorator


def problem_site_statement_zip_view(request, site_key, path):
    problem = get_object_or_404(Problem, problemsite__url_key=site_key)
    statement = query_statement(problem.id)
    return query_zip(statement, path)


@problem_site_tab(_("Problem statement/Submit solution"),
        key='statement', order=100)
def problem_site_statement(request, problem):
    statement = query_statement(problem.id)
    if not statement:
        statement_html = render_to_string(
                'problems/no_problem_statement.html',
                {'problem': problem})
    elif statement.extension == '.zip':
        response = problem_site_statement_zip_view(request,
                problem.problemsite.url_key, 'index.html')
        statement_html = mark_safe(response.content)
    else:
        statement_url = reverse('problem_site_external_statement',
                kwargs={'site_key': problem.problemsite.url_key})
        statement_html = render_to_string(
                'problems/external_statement.html',
                {'problem': problem, 'statement_url': statement_url})

    # To be removed.
    pi = ProblemInstance.objects.get(problem=problem.id)
    submit_url = reverse('submit', kwargs={'contest_id': pi.contest.id})

    return TemplateResponse(request, 'problems/statement_and_submit.html',
            {'statement': statement_html,
             'submit_url': submit_url})


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


@problem_site_tab(_("Submissions"), key='submissions', order=300)
def problem_site_submissions(request, problem):
    # To be changed to Main Problem Instance.
    pi = ProblemInstance.objects.get(problem=problem.id)
    if request.user.is_authenticated():
        submissions_qs = Submission.objects.filter(problem_instance=pi) \
                                           .filter(user=request.user) \
                                           .order_by('-date')
    else:
        submissions_qs = []

    submissions = [{'submission': submission,
                    'can_see_status': True,
                    'can_see_score': True,
                    'can_see_comment': True}
                   for submission in submissions_qs]

    return TemplateResponse(request, 'problems/submissions.html',
        {'submissions': submissions,
         'submissions_on_page': getattr(settings, 'SUBMISSIONS_ON_PAGE', 100),
         'show_scores': True,
         'inside_problem_view': True})
