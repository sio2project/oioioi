from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.template.response import TemplateResponse

from oioioi.programs.models import ProgramSubmission, Test, OutputChecker
from oioioi.programs.utils import decode_str
from oioioi.contests.utils import check_submission_access
from oioioi.base.permissions import enforce_condition
from oioioi.filetracker.utils import stream_file
from oioioi.contests.utils import can_enter_contest

from pygments import highlight
from pygments.lexers import guess_lexer_for_filename
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

# Workaround for race condition in fnmatchcase which is used by pygments
import fnmatch
import sys
fnmatch._MAXCACHE = sys.maxint

@enforce_condition(can_enter_contest)
def show_submission_source_view(request, contest_id, submission_id):
    submission = get_object_or_404(ProgramSubmission, id=submission_id)
    if contest_id != submission.problem_instance.contest_id:
        raise Http404
    check_submission_access(request, submission)
    raw_source = submission.source_file.read()
    raw_source, decode_error = decode_str(raw_source)
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
    download_url = reverse('download_submission_source',
            kwargs={'contest_id': request.contest.id,
                    'submission_id': submission_id})
    return TemplateResponse(request, 'programs/source.html', {
        'source': formatted_source,
        'css': formatted_source_css,
        'is_source_safe': is_source_safe,
        'download_url': download_url,
        'decode_error': decode_error
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

def download_checker_exe_view(request, checker_id):
    checker = get_object_or_404(OutputChecker, id=checker_id)
    if not request.user.has_perm('problems.problem_admin', checker.problem):
        raise PermissionDenied
    if not checker.exe_file:
        raise Http404
    return stream_file(checker.exe_file)
