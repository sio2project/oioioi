import urllib

from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.http import Http404, HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode

from oioioi.problems.models import ProblemStatement, ProblemAttachment
from oioioi.filetracker.utils import stream_file
from oioioi.problems.models import Problem, ProblemPackage
from oioioi.problems.utils import can_admin_problem
from oioioi.problems.problem_sources import problem_sources
from oioioi.contests.utils import is_contest_admin


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


def add_or_update_problem_view(request, contest_id=None):
    sources = problem_sources(request)
    if 'key' not in request.GET:
        qs = request.GET.dict()
        qs['key'] = sources[0].key
        return HttpResponseRedirect(request.path + '?' + urllib.urlencode(qs))
    key = request.GET['key']
    for s in sources:
        if s.key == key:
            current_source = s
            break
    else:
        raise Http404

    contest = contest_id and request.contest

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
            if not contest_id:
                raise PermissionDenied
            if not is_contest_admin(request):
                raise PermissionDenied
    response = current_source.view(request, contest,
            existing_problem=existing_problem)

    if isinstance(response, HttpResponseRedirect):
        return response

    if isinstance(response, TemplateResponse):
        content = response.render().content
    else:
        content = response

    sources_context = []
    qs = request.GET.dict()
    for s in sources:
        qs['key'] = s.key
        link = request.path + '?' + urllib.urlencode(qs)
        sources_context.append({'obj': s, 'link': link})

    context = {
        'sources': sources_context,
        'current_source': current_source,
        'content': mark_safe(force_unicode(content)),
        'existing_problem': existing_problem,
    }
    return TemplateResponse(request, 'problems/add_or_update.html', context)
