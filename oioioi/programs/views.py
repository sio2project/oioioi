import difflib

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse
from django.template.response import TemplateResponse
from django.conf import settings

from oioioi.programs.models import ProgramSubmission, Test, OutputChecker
from oioioi.programs.utils import decode_str
from oioioi.contests.utils import contest_exists, can_enter_contest, \
    get_submission_or_404
from oioioi.base.permissions import enforce_condition
from oioioi.filetracker.utils import stream_file
from pygments import highlight
from pygments.lexers import guess_lexer_for_filename
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

# Workaround for race condition in fnmatchcase which is used by pygments
import fnmatch
import sys
fnmatch._MAXCACHE = sys.maxint


@enforce_condition(contest_exists & can_enter_contest)
def show_submission_source_view(request, contest_id, submission_id):
    submission = get_submission_or_404(request, contest_id, submission_id,
                                       ProgramSubmission)
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
        'decode_error': decode_error,
        'submission_id': submission_id
    })


@enforce_condition(contest_exists & can_enter_contest)
def save_diff_id_view(request, contest_id, submission_id):
    get_submission_or_404(request, contest_id, submission_id,
                          ProgramSubmission)
    request.session['saved_diff_id'] = submission_id
    return HttpResponse()


@enforce_condition(contest_exists & can_enter_contest)
def source_diff_view(request, contest_id, submission1_id, submission2_id):
    if request.session.get('saved_diff_id'):
        request.session.pop('saved_diff_id')
    submission1 = get_submission_or_404(request, contest_id, submission1_id,
                                        ProgramSubmission)
    submission2 = get_submission_or_404(request, contest_id, submission2_id,
                                        ProgramSubmission)
    source1 = submission1.source_file.read()
    source1, decode_error1 = decode_str(source1)
    source2 = submission2.source_file.read()
    source2, decode_error2 = decode_str(source2)
    source1 = source1.splitlines()
    source2 = source2.splitlines()

    numwidth = len(str(max(len(source1), len(source2))))
    ndiff = difflib.ndiff(source1, source2)

    class DiffLine(object):
        def __init__(self, css_class, text, number):
            self.css_class = css_class
            self.text = text
            self.number = number

    def diffstrip(line):
        return line[2:]

    def numformat(num):
        return str(num).rjust(numwidth)

    diff1, diff2 = [], []
    count1, count2 = 1, 1

    for diffline in ndiff:
        line = diffstrip(diffline)
        line = line.expandtabs(4)
        maxlen = getattr(settings, 'CHARACTERS_IN_LINE', 80)
        parts = (len(line) + maxlen) / maxlen
        line = line.ljust(parts * maxlen)
        for i in xrange(parts):
            f, t = i * maxlen, ((i + 1) * maxlen)
            c1, c2 = numformat(count1), numformat(count2)
            if diffline.startswith('- '):
                diff1.append(DiffLine('left', line[f:t], '' if i else c1))
                diff2.append(DiffLine('empty', '', ''))
            elif diffline.startswith('+ '):
                diff1.append(DiffLine('empty', '', ''))
                diff2.append(DiffLine('right', line[f:t], '' if i else c2))
            elif diffline.startswith('  '):
                diff1.append(DiffLine('both', line[f:t], '' if i else c1))
                diff2.append(DiffLine('both', line[f:t], '' if i else c2))
        if diffline.startswith('- ') or diffline.startswith('  '):
            count1 += 1
        if diffline.startswith('+ ') or diffline.startswith('  '):
            count2 += 1

    download_url1 = reverse('download_submission_source',
            kwargs={'contest_id': request.contest.id,
                    'submission_id': submission1_id})
    download_url2 = reverse('download_submission_source',
            kwargs={'contest_id': request.contest.id,
                    'submission_id': submission2_id})

    return TemplateResponse(request, 'programs/source_diff.html',
            {'source1': diff1, 'decode_error1': decode_error1,
             'download_url1': download_url1,
             'source2': diff2, 'decode_error2': decode_error2,
             'download_url2': download_url2,
             'submission1_id': submission1_id,
             'submission2_id': submission2_id,
             'reverse_diff_url': reverse('source_diff', kwargs={
                 'contest_id': contest_id,
                 'submission1_id': submission2_id,
                 'submission2_id': submission1_id})})


@enforce_condition(contest_exists & can_enter_contest)
def download_submission_source_view(request, contest_id, submission_id):
    submission = get_submission_or_404(request, contest_id, submission_id,
                                       ProgramSubmission)
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
