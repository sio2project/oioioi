import logging
import os
import shutil
import sys
import tempfile
from collections import namedtuple
from operator import itemgetter  # pylint: disable=E0611

from django.conf import settings
from django.core.files import File
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from oioioi.base.menu import OrderedRegistry
from oioioi.base.utils import uploaded_file_name
from oioioi.base.utils.archive import Archive
from oioioi.contests.attachment_registration import attachment_registry_problemset
from oioioi.contests.controllers import submission_template_context
from oioioi.contests.forms import SubmissionFormForProblemInstance
from oioioi.contests.models import ProblemInstance, Submission
from oioioi.contests.utils import administered_contests
from oioioi.problems.forms import PackageFileReuploadForm, ProblemStatementReplaceForm
from oioioi.problems.models import (
    AlgorithmTagProposal,
    DifficultyTagProposal,
    Problem,
    ProblemAttachment,
    ProblemPackage,
    ProblemStatement,
)
from oioioi.problems.problem_sources import UploadedPackageSource
from oioioi.problems.utils import (
    can_admin_problem,
    generate_add_to_contest_metadata,
    generate_model_solutions_context,
    query_statement,
    query_zip,
)
from oioioi.sinolpack.models import OriginalPackage
from oioioi.testspackages.models import TestsPackage

problem_site_tab_registry = OrderedRegistry()
logger = logging.getLogger(__name__)


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
    :param condition: a function receiving a request and problem that returns
        if the tab should be accessible for this request
    """

    Tab = namedtuple('Tab', ['view', 'title', 'key', 'condition'])

    if condition is None:
        condition = lambda request, problem: True

    def decorator(func):
        problem_site_tab_registry.register(Tab(func, title, key, condition), order)
        return func

    return decorator


def problem_site_statement_zip_view(request, site_key, path):
    problem = get_object_or_404(Problem, problemsite__url_key=site_key)
    statement = query_statement(problem.id)
    if not statement:
        raise Http404
    return query_zip(statement, path)


def check_for_statement(request, problem):
    """Function checking if given problem has a ProblemStatement."""
    return bool(ProblemStatement.objects.filter(problem=problem))


@problem_site_tab(
    _("Problem statement"), key='statement', order=100, condition=check_for_statement
)
def problem_site_statement(request, problem):
    statement = query_statement(problem.id)
    if not statement:
        statement_html = render_to_string(
            'problems/no-problem-statement.html',
            {'problem': problem,
            'can_admin_problem': can_admin_problem(request, problem)}
        )
    elif statement.extension == '.zip':
        response = problem_site_statement_zip_view(
            request, problem.problemsite.url_key, 'index.html'
        )
        statement_html = render_to_string(
            'problems/from-zip-statement.html',
            {'problem': problem,
            'statement': mark_safe(response.content.decode(errors="replace")),
            'can_admin_problem': can_admin_problem(request, problem)}
        )
    else:
        statement_url = reverse(
            'problem_site_external_statement',
            kwargs={'site_key': problem.problemsite.url_key},
        )
        statement_html = render_to_string(
            'problems/external-statement.html',
            {'problem': problem,
            'statement_url': statement_url,
            'can_admin_problem': can_admin_problem(request, problem)},
        )

    return statement_html


def check_for_downloads(request, problem):
    """Function checking if given problem has any downloadables."""
    return bool(ProblemAttachment.objects.filter(problem=problem)) or bool(
        attachment_registry_problemset.to_list(request=request, problem=problem)
    )


@problem_site_tab(_("Downloads"), key='files', order=200, condition=check_for_downloads)
def problem_site_files(request, problem):
    additional_files = attachment_registry_problemset.to_list(
        request=request, problem=problem
    )
    files_qs = ProblemAttachment.objects.filter(problem=problem.id)
    files = sorted(
        [
            {
                'name': f.filename,
                'description': f.description,
                'link': reverse(
                    'problem_site_external_attachment',
                    kwargs={
                        'site_key': problem.problemsite.url_key,
                        'attachment_id': f.id,
                    },
                ),
            }
            for f in files_qs
        ],
        key=itemgetter('name'),
    )
    files.extend(additional_files)

    return TemplateResponse(
        request,
        'problems/files.html',
        {
            'files': files,
            'files_on_page': getattr(settings, 'FILES_ON_PAGE', 100),
            'add_category_field': False,
        },
    )


@problem_site_tab(
    _("Submissions"),
    key='submissions',
    order=300,
    condition=lambda request, problem: not request.contest,
)
def problem_site_submissions(request, problem):
    controller = problem.main_problem_instance.controller
    if request.user.is_authenticated:
        qs = controller.filter_my_visible_submissions(
            request,
            Submission.objects.filter(
                problem_instance=problem.main_problem_instance
            ).order_by('-date'),
        )
    else:
        qs = []

    submissions = [submission_template_context(request, s) for s in qs]
    show_scores = any(s['can_see_score'] for s in submissions)

    return TemplateResponse(
        request,
        'problems/submissions.html',
        {
            'submissions': submissions,
            'submissions_on_page': getattr(settings, 'SUBMISSIONS_ON_PAGE', 100),
            'show_scores': show_scores,
            'inside_problem_view': True,
        },
    )


@problem_site_tab(
    _("Submit"),
    key='submit',
    order=400,
    condition=lambda request, problem: not request.contest,
)
def problem_site_submit(request, problem):
    pi = problem.main_problem_instance
    if request.method == 'POST':
        form = SubmissionFormForProblemInstance(
            request, pi, request.POST, request.FILES
        )
        if form.is_valid():
            pi.controller.create_submission(request, pi, form.cleaned_data)
            url = reverse(
                'problem_site', kwargs={'site_key': problem.problemsite.url_key}
            )
            return redirect(url + '?key=submissions')
    else:
        form = SubmissionFormForProblemInstance(request, pi)

    return TemplateResponse(
        request, 'problems/submit.html', {'problem': problem, 'form': form}
    )


@problem_site_tab(
    _("Secret key"),
    key='secret_key',
    order=500,
    condition=lambda request, problem: problem.visibility != problem.VISIBILITY_PUBLIC,
)
def problem_site_secret_key(request, problem):
    return TemplateResponse(
        request, 'problems/secret-key.html', {'site_key': problem.problemsite.url_key}
    )


@problem_site_tab(_("Settings"), key='settings', order=600, condition=can_admin_problem)
def problem_site_settings(request, problem):
    _, administered_recent_contests = generate_add_to_contest_metadata(request)
    package = ProblemPackage.objects.filter(problem=problem).first()
    problem_instance = get_object_or_404(
        ProblemInstance, id=problem.main_problem_instance_id
    )
    model_solutions = generate_model_solutions_context(request, problem_instance)
    extra_actions = problem.controller.get_extra_problem_site_actions(problem)
    algorithm_tag_proposals = (
        AlgorithmTagProposal.objects.all().filter(problem=problem).order_by('-pk')[:25]
    )
    difficulty_tag_proposals = (
        DifficultyTagProposal.objects.all().filter(problem=problem).order_by('-pk')[:25]
    )

    return TemplateResponse(
        request,
        'problems/settings.html',
        {
            'site_key': problem.problemsite.url_key,
            'problem': problem,
            'administered_recent_contests': administered_recent_contests,
            'package': package if package and package.package_file else None,
            'model_solutions': model_solutions,
            'algorithm_tag_proposals': algorithm_tag_proposals,
            'difficulty_tag_proposals': difficulty_tag_proposals,
            'can_admin_problem': can_admin_problem(request, problem),
            'extra_actions': extra_actions,
        },
    )


@problem_site_tab(_("Add to contest"), key='add_to_contest', order=700)
def problem_site_add_to_contest(request, problem):
    administered = administered_contests(request)
    administered = sorted(administered, key=lambda x: x.creation_date, reverse=True)
    tests_package = TestsPackage.objects.filter(problem=problem)
    tests_package_visible = any(
        [tp.is_visible(request.timestamp) for tp in tests_package]
    )
    return TemplateResponse(
        request,
        'problems/add-to-contest.html',
        {
            'site_key': problem.problemsite.url_key,
            'contests': administered,
            'tests_package_visible': tests_package_visible,
        },
    )


@problem_site_tab(
    _("Replace problem statement"),
    key='replace_problem_statement',
    order=800,
    condition=can_admin_problem,
)
def problem_site_replace_statement(request, problem):
    statements = ProblemStatement.objects.filter(problem=problem)
    filenames = [statement.filename for statement in statements]

    if request.method == 'POST':
        form = PackageFileReuploadForm(filenames, request.POST, request.FILES)
        if form.is_valid():
            statement_filename = form.cleaned_data['file_name']
            statements = [s for s in statements if s.filename == statement_filename]
            if statements:
                statement = statements[0]
                new_statement_file = form.cleaned_data['file_replacement']
                statement.content = new_statement_file
                statement.save()
                url = reverse(
                    'problem_site', kwargs={'site_key': problem.problemsite.url_key}
                )
                return redirect(url + '?key=replace_problem_statement')
            else:
                form.add_error(None, _("Picked statement file does not exist."))
    else:
        form = ProblemStatementReplaceForm(filenames)
    return TemplateResponse(
        request,
        'problems/replace-problem-statement.html',
        {'form': form, 'problem': problem},
    )


def _prepare_changed_package(request, form, archive, package_name):
    file_path = request.POST.get("file_name", None)
    if len(request.FILES) != 1:
        form.add_error('file_replacement', _("File replacement not provided"))
        return None, None
    uploaded_file = next(request.FILES.values())
    if uploaded_file.name != os.path.basename(file_path):
        form.add_error(
            None, _("Original and replacement files must have the same name")
        )
        return None, None

    extraction_dir = tempfile.mkdtemp()
    archive.extract(to_path=extraction_dir)
    file_path = os.path.join(extraction_dir, file_path)
    with open(file_path, "wb") as original_file:
        original_file.write(uploaded_file.read())
    package_dir = tempfile.mkdtemp()
    package_archive_name = os.path.join(package_dir, package_name)
    shutil.make_archive(
        base_name=package_archive_name, format='zip', root_dir=extraction_dir
    )
    package_archive_name += '.zip'
    shutil.rmtree(extraction_dir)
    return package_archive_name, package_dir


def _problem_can_be_reuploaded(request, problem):
    return len(ProblemInstance.objects.filter(problem=problem)) <= 2


@problem_site_tab(
    _("Manage package files"),
    key='manage_files_problem_package',
    order=900,
    condition=can_admin_problem,
)
def problem_site_package_download_file(request, problem):
    original_package = OriginalPackage.objects.filter(problem=problem)

    # Check for existence of original package -- e.g. quizzes don't have it.
    if not original_package.exists():
        return TemplateResponse(request, 'problems/files.html', {'files': False})
    original_package = original_package.get()
    problem = original_package.problem
    package = original_package.problem_package
    contest = problem.contest
    archive = Archive(package.package_file)
    file_names = archive.filenames()
    if request.method == 'POST':
        form = PackageFileReuploadForm(file_names, request.POST)
        if form.is_valid():
            if 'upload_button' in request.POST:
                package_name = file_names[0].split(os.path.sep, 1)[0]
                package_archive, tmpdir = _prepare_changed_package(
                    request, form, archive, package_name
                )
                if package_archive is not None:
                    package_file = File(
                        open(package_archive, 'rb'), os.path.basename(package_archive)
                    )
                    original_filename = package_file.name
                    file_manager = uploaded_file_name(package_file)
                    source = UploadedPackageSource()
                    try:
                        source.process_package(
                            request,
                            file_manager,
                            request.user,
                            contest,
                            existing_problem=problem,
                            original_filename=original_filename,
                            visibility=problem.visibility,
                        )
                    except Exception as e:
                        logger.error(
                            "Error processing package",
                            exc_info=True,
                            extra={'omit_sentry': True},
                        )
                        form._errors['__all__'] = form.error_class([smart_str(e)])
                    finally:
                        shutil.rmtree(tmpdir)
                    return source._redirect_response(request)
            elif 'download_button' in request.POST:
                file_name = request.POST.get('file_name', None)
                if file_name is None:
                    form.add_error('file_name', _("No file selected"))
                else:
                    return redirect(
                        'download_package_file',
                        package_id=package.id,
                        file_name=file_name,
                    )
    else:
        form = PackageFileReuploadForm(file_names)
    return TemplateResponse(
        request,
        'problems/manage-problem-package-files.html',
        {'form': form, 'can_reupload': _problem_can_be_reuploaded(request, problem)},
    )
