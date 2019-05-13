# coding: utf-8
import urllib
from collections import defaultdict
from functools import wraps
import re

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Case, F, When
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
import six.moves.urllib.parse

from oioioi.base.utils import jsonify, tabbed_view
from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.models import (ProblemInstance, Submission,
                                    SubmissionReport)
from oioioi.contests.utils import administered_contests, is_contest_admin
from oioioi.filetracker.utils import stream_file
from oioioi.problems.forms import ProblemsetSourceForm
from oioioi.problems.models import (Problem, ProblemAttachment, ProblemPackage,
                                    ProblemStatement, Tag, OriginTag,
                                    DifficultyTag, AlgorithmTag)

from oioioi.problems.menu import navbar_links_registry
from oioioi.problems.problem_site import problem_site_tab_registry
from oioioi.problems.problem_sources import problem_sources
from oioioi.problems.utils import (can_add_to_problemset, can_admin_instance_of_problem,
                                   can_admin_problem, can_admin_problem_instance,
                                   generate_add_to_contest_metadata, generate_model_solutions_context,
                                   query_statement)
from oioioi.programs.models import (GroupReport, ModelProgramSubmission,
                                    ModelSolution, TestReport)
from unidecode import unidecode


# problem_site_statement_zip_view is used in one of the tabs
# in problem_site.py. We placed the view in problem_site.py
# instead of views.py to avoid circular imports. We still import
# it here to use it in urls.py.
from oioioi.problems.problem_site import problem_site_statement_zip_view


if settings.CONTEST_MODE == ContestMode.neutral:
    navbar_links_registry.register(
        name='contests_list',
        text=_('Contests'),
        url_generator=lambda request: reverse('select_contest'),
        order=100,
    )

navbar_links_registry.register(
    name='problemset',
    text=_('Problemset'),
    url_generator=lambda request: reverse('problemset_main'),
    order=200,
)

navbar_links_registry.register(
    name='task_archive',
    text=_('Task archive'),
    # TODO Change the following URL when the Task Archive
    #      gets moved from the global portal on Szkopul.
    url_generator=lambda request:
        reverse('global_portal',
            kwargs={'link_name': 'default',
                    'portal_path': 'problemset' + ('_eng' if request.LANGUAGE_CODE != 'pl' else '')}),
    order=300,
)


def show_statement_view(request, statement_id):
    statement = get_object_or_404(ProblemStatement, id=statement_id)
    if not can_admin_instance_of_problem(request, statement.problem):
        raise PermissionDenied
    return stream_file(statement.content, statement.download_name)


def show_problem_attachment_view(request, attachment_id):
    attachment = get_object_or_404(ProblemAttachment, id=attachment_id)
    if not can_admin_instance_of_problem(request, attachment.problem):
        raise PermissionDenied
    return stream_file(attachment.content, attachment.download_name)


def _get_package(request, package_id):
    package = get_object_or_404(ProblemPackage, id=package_id)
    has_perm = False
    if package.contest:
        has_perm = request.user.has_perm('contests.contest_admin',
                package.contest)
    elif package.problem:
        has_perm = can_admin_problem(request, package.problem)
    else:
        has_perm = request.user.is_superuser
    if not has_perm:
        raise PermissionDenied
    return package


def download_problem_package_view(request, package_id):
    package = _get_package(request, package_id)
    return stream_file(package.package_file, package.download_name)


def download_package_traceback_view(request, package_id):
    package = _get_package(request, package_id)
    if not package.traceback:
        raise Http404
    return stream_file(package.traceback, 'package_%s_%d_traceback.txt' % (
            package.problem_name, package.id))


def add_or_update_problem(request, contest, template):
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
            if contest and (not is_contest_admin(request)):
                raise PermissionDenied

    navbar_links = navbar_links_registry.template_context(request)
    problemset_tabs = generate_problemset_tabs(request)

    context = {'existing_problem': existing_problem, 'navbar_links': navbar_links,
               'problemset_tabs': problemset_tabs}
    tab_kwargs = {
        'contest': contest,
        'existing_problem': existing_problem
    }

    tab_link_params = request.GET.dict()

    def build_link(tab):
        tab_link_params['key'] = tab.key
        return request.path + '?' + six.moves.urllib.parse.urlencode(
                tab_link_params)

    return tabbed_view(request, template, context,
            problem_sources(request), tab_kwargs, build_link)


@transaction.non_atomic_requests
def add_or_update_problem_view(request):
    return add_or_update_problem(request, request.contest,
                                 'problems/add-or-update.html')


def search_problems_in_problemset(datadict):

    try:
        query = datadict['q']
        if not query:
            return Problem.objects.all(), ''

        # query_phrases is list containing all phrases from query - phrase is
        # compact string (without blank characters) or any string inside "...",
        # there are special phrases with prefix 'name:' or 'tag:' if phrase
        # prefix is one of those, rest of phrase would be treated as regular
        # phrase; for example if
        # query='word "two words" tag:example name:"Example name"' then
        # query_phrases=['word', 'two words', 'tag:example', 'name:Example name']
        # (note no quotation marks)
        query_phrases = [re.sub(r'"(.*?)"', r'\1', match).strip() for match in
                         re.findall(r'(?:tag:|name:)?(?:".+?"|\w+)',
                                    query, flags=re.UNICODE)]

        problems = Problem.objects.none()
        for phrase in query_phrases:
            if phrase.startswith('tag:'):
                problems |= Problem.objects.filter(tag__name=phrase[len('tag:'):])
                problems |= Problem.objects.filter(algorithmtag__name=phrase[len('tag:'):])
                problems |= Problem.objects.filter(origintag__name=phrase[len('tag:'):])
                problems |= Problem.objects.filter(difficultytag__name=phrase[len('tag:'):])
            elif phrase.startswith('name:'):
                problems |= Problem.objects.filter(name=phrase[len('name:'):])
            else:
                problems |= Problem.objects.filter(ascii_name__icontains=unidecode(phrase))
                problems |= Problem.objects.filter(tag__name__icontains=unidecode(phrase))
                problems |= Problem.objects.filter(algorithmtag__name__icontains=unidecode(phrase))
                problems |= Problem.objects.filter(origintag__name__icontains=unidecode(phrase))
                problems |= Problem.objects.filter(difficultytag__name__icontains=unidecode(phrase))
        problems = problems.distinct()
        return problems, query

    except KeyError:
        return Problem.objects.all(), ''


def generate_problemset_tabs(request):
    tabs = []

    tabs.append({'name': _('Public problems'), 'url': reverse('problemset_main')})

    if request.user.is_authenticated:
        tabs.append({'name': _('My problems'), 'url': reverse('problemset_my_problems')})

        if request.user.is_superuser:
            tabs.append({'name': _('All problems'), 'url': reverse('problemset_all_problems')})
        if can_add_to_problemset(request):
            tabs.append({'name': _('Add problem'), 'url': reverse('problemset_add_or_update')})

    return tabs



def problemset_get_problems(request):
    problems, query = search_problems_in_problemset(request.GET)

    if settings.PROBLEM_STATISTICS_AVAILABLE:
        # We need to annotate all of the statistics, because NULLs are difficult
        # to sort by before Django 1.11, this can be changed if we upgrade...
        problems = problems.select_related('statistics').annotate(
            statistics_submitted=Case(
                When(statistics__isnull=True, then=0),
                default=F('statistics__submitted')
            ),
            statistics_solved_pc=Case(
                When(statistics__isnull=True, then=0),
                When(statistics__submitted=0, then=0),
                default=100*F('statistics__solved')/F('statistics__submitted')
            ),
            statistics_avg_best_score=Case(
                When(statistics__isnull=True, then=0),
                default=F('statistics__avg_best_score')
            )
        )

    order_fields = ('name', 'short_name')
    order_statistics = ('submitted', 'solved_pc', 'avg_best_score')
    if 'order_by' in request.GET:
        field = request.GET['order_by']
        if field in order_fields:
            problems = problems \
                .order_by(('-' if 'desc' in request.GET else '') + field)
        elif field in order_statistics:
            problems = problems \
                .order_by(('-' if 'desc' in request.GET else '')
                          + 'statistics_' + field)
        else:
            raise Http404

    problems = problems.select_related('problemsite')
    problems = problems.prefetch_related('tag_set', 'algorithmtag_set',
                                         'origintag_set', 'difficultytag_set')
    return problems, query


def problemset_generate_view(request, page_title, problems, query_string, view_type):
    # We want to show "Add to contest" button only
    # if user is contest admin for any contest.
    show_add_button, administered_recent_contests = \
        generate_add_to_contest_metadata(request)
    show_tags = settings.PROBLEM_TAGS_VISIBLE
    show_statistics = settings.PROBLEM_STATISTICS_AVAILABLE
    col_proportions = {
        'id': 2,
        'name': 2,
        'tags': 4,
        'statistics1': 1,
        'statistics2': 1,
        'statistics3': 1,
        'add_button': 1
    }
    if not show_add_button:
        col_proportions['tags'] += col_proportions.pop('add_button')
    if not show_statistics:
        col_proportions['id'] += col_proportions.pop('statistics1')
        col_proportions['name'] += col_proportions.pop('statistics2')
        col_proportions['tags'] += col_proportions.pop('statistics3')
    if not show_tags:
        col_proportions['name'] += col_proportions.pop('tags')
    assert sum(col_proportions.values()) == 12
    form = ProblemsetSourceForm("")

    navbar_links = navbar_links_registry.template_context(request)
    problemset_tabs = generate_problemset_tabs(request)

    return TemplateResponse(request,
       'problems/problemset/problem-list.html',
      {'problems': problems,
       'navbar_links': navbar_links,
       'problemset_tabs': problemset_tabs,
       'page_title': page_title,
        'select_problem_src': request.GET.get('select_problem_src'),
       'problem_search': query_string,
       'show_tags': show_tags,
       'show_statistics': show_statistics,
       'show_search_bar': True,
       'show_add_button': show_add_button,
       'administered_recent_contests': administered_recent_contests,
       'col_proportions': col_proportions,
       'form': form,
       'view_type': view_type})


def problemset_main_view(request):
    page_title = \
        _("Welcome to problemset, the place where all the problems are.")
    problems_pool, query_string = problemset_get_problems(request)
    problems = problems_pool.filter(is_public=True, problemsite__isnull=False)

    return problemset_generate_view(request, page_title, problems, query_string, "public")


def problemset_my_problems_view(request):
    page_title = _("My problems")
    problems_pool, query_string = problemset_get_problems(request)
    problems = problems_pool.filter(author=request.user, problemsite__isnull=False)
    return problemset_generate_view(request, page_title, problems, query_string, "my")


def problemset_all_problems_view(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    page_title = _("All problems")
    problems_pool, query_string = problemset_get_problems(request)
    problems = problems_pool.filter(problemsite__isnull=False)

    return problemset_generate_view(request, page_title, problems, query_string, "all")


def problem_site_view(request, site_key):
    problem = get_object_or_404(Problem, problemsite__url_key=site_key)
    package = ProblemPackage.objects.filter(problem=problem).first()
    show_add_button, administered_recent_contests = \
        generate_add_to_contest_metadata(request)
    extra_actions = problem.controller.get_extra_problem_site_actions(problem)
    navbar_links = navbar_links_registry.template_context(request)
    problemset_tabs = generate_problemset_tabs(request)
    problemset_tabs.append({'name': _('Problem view'), 'url': reverse('problem_site', kwargs={'site_key': site_key})})
    context = {'problem': problem,
               'package': package if package and package.package_file
                        else None,
               'extra_actions': extra_actions,
               'can_admin_problem': can_admin_problem(request, problem),
               'select_problem_src': request.GET.get('select_problem_src'),
               'show_add_button': show_add_button,
               'administered_recent_contests': administered_recent_contests,
               'navbar_links': navbar_links,
               'problemset_tabs': problemset_tabs}
    tab_kwargs = {'problem': problem}

    tab_link_params = request.GET.dict()
    if 'page' in tab_link_params:
        del tab_link_params['page']

    def build_link(tab):
        tab_link_params['key'] = tab.key
        return request.path + '?' + six.moves.urllib.parse.urlencode(
                tab_link_params)

    return tabbed_view(request, 'problems/problemset/problem-site.html',
            context, problem_site_tab_registry, tab_kwargs, build_link)


def problem_site_external_statement_view(request, site_key):
    problem = get_object_or_404(Problem, problemsite__url_key=site_key)
    statement = query_statement(problem.id)
    if statement.extension == '.zip' \
            and not can_admin_problem(request, problem):
        raise PermissionDenied
    return stream_file(statement.content, statement.download_name)


def problem_site_external_attachment_view(request, site_key, attachment_id):
    problem = get_object_or_404(Problem, problemsite__url_key=site_key)
    attachment = get_object_or_404(ProblemAttachment, id=attachment_id)
    if attachment.problem.id != problem.id:
        raise PermissionDenied
    return stream_file(attachment.content, attachment.download_name)


def problemset_add_to_contest_view(request, site_key):
    problem_name = request.GET.get('problem_name')
    if not problem_name:
        raise Http404
    administered = administered_contests(request)
    administered = sorted(administered,
        key=lambda x: x.creation_date, reverse=True)
    navbar_links = navbar_links_registry.template_context(request)
    problemset_tabs = generate_problemset_tabs(request)
    problemset_tabs.append({'name': _('Add to contest'), 'url': reverse('problemset_add_to_contest',
                                                                    kwargs={'site_key': site_key})})
    return TemplateResponse(request, 'problems/problemset/select-contest.html',
                            {'site_key': site_key,
                             'administered_contests': administered,
                             'problem_name': problem_name,
                             'navbar_links': navbar_links,
                             'problemset_tabs': problemset_tabs})


def get_report_HTML_view(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    controller = submission.problem_instance.controller
    if not controller.filter_my_visible_submissions(request, Submission.objects
                            .filter(id=submission_id)).exists():
        raise Http404
    reports = ''
    queryset = SubmissionReport.objects.filter(submission=submission). \
        prefetch_related('scorereport_set')
    for report in controller.filter_visible_reports(request, submission,
            queryset.filter(status='ACTIVE')):
        reports += controller.render_report(request, report)

    if not reports:
        reports = _(u"Reports are not available now (ಥ ﹏ ಥ)")
        reports = mark_safe('<center>' + reports + '</center>')
    return HttpResponse(reports)


@transaction.non_atomic_requests
def problemset_add_or_update_problem_view(request):
    if not can_add_to_problemset(request):
        if request.contest:
            url = reverse('add_or_update_problem') + '?' + \
                six.moves.urllib.parse.urlencode(request.GET.dict())
            return safe_redirect(request, url)
        raise PermissionDenied

    return add_or_update_problem(request, None,
                                 'problems/problemset/add-or-update.html')


def model_solutions_view(request, problem_instance_id):
    context = generate_model_solutions_context(request, problem_instance_id)

    return TemplateResponse(request, 'programs/admin/model_solutions.html',
            context)


def rejudge_model_solutions_view(request, problem_instance_id):
    problem_instance = \
            get_object_or_404(ProblemInstance, id=problem_instance_id)
    contest = problem_instance.contest
    if not request.user.has_perm('contests.contest_admin', contest):
        raise PermissionDenied
    ModelSolution.objects.recreate_model_submissions(problem_instance)
    messages.info(request, _("Model solutions sent for evaluation."))
    return redirect('model_solutions', problem_instance.id)


@jsonify
def get_origintag_hints_view(request):
    substr = request.GET.get('substr', '')
    if len(substr) < 2:
        raise Http404
    num_hints = getattr(settings, 'NUM_HINTS', 10)
    queryset_tags = OriginTag.objects.filter(name__icontains=substr)[:num_hints].all()
    return [str(tag.name) for tag in queryset_tags]


@jsonify
def get_difficultytag_hints_view(request):
    substr = request.GET.get('substr', '')
    if len(substr) < 2:
        raise Http404
    num_hints = getattr(settings, 'NUM_HINTS', 10)
    queryset_tags = DifficultyTag.objects.filter(name__icontains=substr)[:num_hints].all()
    return [str(tag.name) for tag in queryset_tags]


@jsonify
def get_algorithmtag_hints_view(request):
    substr = request.GET.get('substr', '')
    if len(substr) < 2:
        raise Http404
    num_hints = getattr(settings, 'NUM_HINTS', 10)
    queryset_tags = AlgorithmTag.objects.filter(name__icontains=substr)[:num_hints].all()
    return [str(tag.name) for tag in queryset_tags]


@jsonify
def get_tag_hints_view(request):
    substr = request.GET.get('substr', '')
    if len(substr) < 2:
        raise Http404
    num_hints = getattr(settings, 'NUM_HINTS', 10)
    queryset_tags = Tag.objects.filter(name__icontains=substr)[:num_hints].all()
    return [str(tag.name) for tag in queryset_tags]


@jsonify
def get_search_hints_view(request, view_type):
    substr = request.GET.get('substr', '')
    if len(substr) < 2:
        raise Http404
    num_hints = getattr(settings, 'NUM_HINTS', 10)
    queryset_problems = Problem.objects.none
    if view_type == 'public':
        queryset_problems = \
            Problem.objects.filter(name__icontains=substr, is_public=True,
                                   problemsite__isnull=False)[:num_hints].all()
    elif view_type == 'my':
        queryset_problems = \
            Problem.objects.filter(name__icontains=substr, author=request.user,
                                       problemsite__isnull=False)[:num_hints].all()
    elif view_type == 'all':
        queryset_problems = Problem.objects.filter(name__icontains=substr,
                                       problemsite__isnull=False)[:num_hints].all()
    queryset_tags = Tag.objects.filter(name__icontains=substr)[:num_hints].all()
    queryset_algorithmtags = AlgorithmTag.objects.filter(name__icontains=substr)[:num_hints].all()
    queryset_origintags = OriginTag.objects.filter(name__icontains=substr)[:num_hints].all()
    queryset_difficultytags = DifficultyTag.objects.filter(name__icontains=substr)[:num_hints].all()

    return list(set(problem.name for problem in queryset_problems) |
                set(tag.name for tag in queryset_tags) |
                set(tag.name for tag in queryset_origintags) |
                set(tag.name for tag in queryset_algorithmtags) |
                set(tag.name for tag in queryset_difficultytags))[:num_hints]
