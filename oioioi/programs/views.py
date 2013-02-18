from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.template.response import TemplateResponse

from oioioi.programs.models import ProgramSubmission, Test
from oioioi.contests.views import check_submission_access
from oioioi.base.permissions import enforce_condition
from oioioi.filetracker.utils import stream_file
from oioioi.contests.utils import can_enter_contest

from pygments import highlight
from pygments.lexers import guess_lexer_for_filename
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

@enforce_condition(can_enter_contest)
def show_submission_source_view(request, contest_id, submission_id):
    submission = get_object_or_404(ProgramSubmission, id=submission_id)
    if contest_id != submission.problem_instance.contest_id:
        raise Http404
    check_submission_access(request, submission)
    raw_source = submission.source_file.read().decode('utf-8', 'replace')
    filename = submission.source_file.file.name
    is_source_safe = False
    try:
        lexer = guess_lexer_for_filename(
            filename,
            raw_source
        )
        formatter = HtmlFormatter(linenos=True, line_number_chars=3,
                            cssclass='syntax-highlight')
        formatted_source = highlight(raw_source, lexer, formatter)
        formatted_source_css = HtmlFormatter() \
                .get_style_defs('.syntax-highlight')
        is_source_safe = True
    except ClassNotFound:
        formatted_source = raw_source
        formatted_source_css = ''
    return TemplateResponse(request, 'programs/source.html', {
        'source': formatted_source,
        'css': formatted_source_css,
        'is_source_safe': is_source_safe
    })

@enforce_condition(can_enter_contest)
def download_submission_source_view(request, contest_id, submission_id):
    submission = get_object_or_404(ProgramSubmission, id=submission_id)
    if contest_id != submission.problem_instance.contest_id:
        raise Http404
    check_submission_access(request, submission)
    return stream_file(submission.source_file)

def download_input_file_view(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if not request.user.has_perm('problems.problem_admin', test.problem):
        raise PermissionDenied
    return stream_file(test.input_file)

def download_output_file_view(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if not request.user.has_perm('problems.problem_admin', test.problem):
        raise PermissionDenied
    return stream_file(test.output_file)
