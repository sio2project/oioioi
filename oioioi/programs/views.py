import difflib

# Workaround for race condition in fnmatchcase which is used by pygments
import fnmatch
import logging
import os
import shutil
import sys
import tempfile
import zipfile

from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.files import File
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from pygments import highlight

# pylint: disable=no-name-in-module
from pygments.formatters import HtmlFormatter
from pygments.lexers import guess_lexer_for_filename
from pygments.util import ClassNotFound

from oioioi.base.permissions import enforce_condition
from oioioi.base.utils import jsonify, strip_num_or_hash
from oioioi.contests.utils import (
    can_enter_contest,
    contest_exists,
    get_submission_or_error,
    is_contest_basicadmin,
    submittable_problem_instances,
)
from oioioi.filetracker.utils import stream_file
from oioioi.programs.models import (
    OutputChecker,
    ProblemInstance,
    ProgramSubmission,
    SubmissionReport,
    Test,
    TestReport,
    UserOutGenStatus,
)
from oioioi.programs.problem_instance_utils import get_language_by_extension
from oioioi.programs.utils import (
    decode_str,
    get_extension,
    get_submission_source_file_or_error,
    get_submittable_languages,
)

fnmatch._MAXCACHE = sys.maxsize

logger = logging.getLogger(__name__)


@enforce_condition(~contest_exists | can_enter_contest)
def show_submission_source_view(request, submission_id):
    source_file = get_submission_source_file_or_error(request, submission_id)
    raw_source, decode_error = decode_str(source_file.read())
    filename = source_file.file.name
    is_source_safe = False
    try:
        lexer = guess_lexer_for_filename(filename, raw_source)
        formatter = HtmlFormatter(
            linenos=True, line_number_chars=3, cssclass='syntax-highlight'
        )
        formatted_source = highlight(raw_source, lexer, formatter)
        formatted_source_css = HtmlFormatter().get_style_defs('.syntax-highlight')
        is_source_safe = True
    except ClassNotFound:
        formatted_source = raw_source
        formatted_source_css = ''
    download_url = reverse(
        'download_submission_source', kwargs={'submission_id': submission_id}
    )
    return TemplateResponse(
        request,
        'programs/source.html',
        {
            'raw_source': raw_source,
            'source': formatted_source,
            'css': formatted_source_css,
            'is_source_safe': is_source_safe,
            'download_url': download_url,
            'decode_error': decode_error,
            'submission_id': submission_id,
        },
    )


@enforce_condition(~contest_exists | can_enter_contest)
def save_diff_id_view(request, submission_id):
    # Verify user's access to the submission
    get_submission_source_file_or_error(request, submission_id)
    request.session['saved_diff_id'] = submission_id
    return HttpResponse()


@enforce_condition(~contest_exists | can_enter_contest)
def source_diff_view(request, submission1_id, submission2_id):
    if request.session.get('saved_diff_id'):
        request.session.pop('saved_diff_id')
    source1 = get_submission_source_file_or_error(request, submission1_id).read()
    source2 = get_submission_source_file_or_error(request, submission2_id).read()

    source1, decode_error1 = decode_str(source1)
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
        parts = (len(line) + maxlen) // maxlen
        line = line.ljust(parts * maxlen)
        for i in range(parts):
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

    download_url1 = reverse(
        'download_submission_source', kwargs={'submission_id': submission1_id}
    )
    download_url2 = reverse(
        'download_submission_source', kwargs={'submission_id': submission2_id}
    )

    return TemplateResponse(
        request,
        'programs/source_diff.html',
        {
            'source1': diff1,
            'decode_error1': decode_error1,
            'download_url1': download_url1,
            'source2': diff2,
            'decode_error2': decode_error2,
            'download_url2': download_url2,
            'submission1_id': submission1_id,
            'submission2_id': submission2_id,
            'reverse_diff_url': reverse(
                'source_diff',
                kwargs={
                    'submission1_id': submission2_id,
                    'submission2_id': submission1_id,
                },
            ),
        },
    )


@enforce_condition(~contest_exists | can_enter_contest)
def download_submission_source_view(request, submission_id):
    source_file = get_submission_source_file_or_error(request, submission_id)
    return stream_file(source_file)


def download_input_file_view(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if not test.problem_instance.controller.can_see_test(request, test):
        raise PermissionDenied
    return stream_file(test.input_file, strip_num_or_hash(test.input_file.name))


def download_output_file_view(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if not test.problem_instance.controller.can_see_test(request, test):
        raise PermissionDenied
    return stream_file(test.output_file, strip_num_or_hash(test.output_file.name))


def download_checker_exe_view(request, checker_id):
    checker = get_object_or_404(OutputChecker, id=checker_id)
    if not test.problem_instance.controller.can_see_checker_exe(request, test):
        raise PermissionDenied
    if not checker.exe_file:
        raise Http404
    return stream_file(checker.exe_file, strip_num_or_hash(checker.exe_file.name))


def _check_generate_out_permission(request, submission_report):
    if request.contest.id != submission_report.submission.problem_instance.contest_id:
        raise PermissionDenied
    if not request.contest.controller.can_generate_user_out(request, submission_report):
        raise PermissionDenied


def _userout_filename(testreport):
    return (
        testreport.test_name
        + '_user_out_'
        + str(testreport.submission_report.submission.user)
        + '_'
        + str(testreport.submission_report.id)
        + '.out'
    )


def _check_generated_out_visibility_for_user(testreport):
    try:
        if testreport.userout_status.visible_for_user is False:
            raise Http404
    except UserOutGenStatus.DoesNotExist:
        # no UserOutGenStatus means that output has not been generated by \
        # admin or user
        pass


@enforce_condition(contest_exists & can_enter_contest)
def download_user_one_output_view(request, testreport_id):
    testreport = get_object_or_404(TestReport, id=testreport_id)

    if not is_contest_basicadmin(request):
        _check_generated_out_visibility_for_user(testreport)

    submission_report = testreport.submission_report
    _check_generate_out_permission(request, submission_report)

    if not bool(testreport.output_file):
        raise Http404

    return stream_file(testreport.output_file, _userout_filename(testreport))


@enforce_condition(contest_exists & can_enter_contest)
def download_user_all_output_view(request, submission_report_id):
    submission_report = get_object_or_404(SubmissionReport, id=submission_report_id)
    _check_generate_out_permission(request, submission_report)

    testreports = TestReport.objects.filter(submission_report=submission_report)
    if not all(bool(report.output_file) for report in testreports):
        raise Http404

    if not is_contest_basicadmin(request):
        for report in testreports:
            _check_generated_out_visibility_for_user(report)

    zipfd, tmp_zip_filename = tempfile.mkstemp()
    with zipfile.ZipFile(os.fdopen(zipfd, 'wb'), 'w') as zip:
        for report in testreports:
            arcname = _userout_filename(report)
            testfd, tmp_test_filename = tempfile.mkstemp()
            fileobj = os.fdopen(testfd, 'wb')
            try:
                shutil.copyfileobj(report.output_file, fileobj)
                fileobj.close()
                zip.write(tmp_test_filename, arcname)
            finally:
                os.unlink(tmp_test_filename)

        name = submission_report.submission.problem_instance.problem.short_name
        return stream_file(
            File(
                open(tmp_zip_filename, 'rb'),
                name=name
                + '_'
                + str(submission_report.submission.user)
                + '_'
                + str(submission_report.id)
                + '_user_outs.zip',
            )
        )


def _testreports_to_generate_outs(request, testreports):
    """Gets tests' ids from ``testreports`` without generated or processing
    right now outs. Returns list of tests' ids.
    """
    test_ids = []

    for testreport in testreports:
        (
            download_control,
            created,
        ) = UserOutGenStatus.objects.select_for_update().get_or_create(
            testreport=testreport
        )

        if not created:
            if not is_contest_basicadmin(request):
                # out generated by admin is now visible for user
                download_control.visible_for_user = True
                download_control.save()

            # making sure, that output really exists or is processing right now
            if bool(testreport.output_file) or download_control.status == '?':
                # out already generated or is processing, omit
                continue
            else:
                download_control.status = '?'
                download_control.save()
        elif bool(testreport.output_file):
            # out already generated but without UserOutGenStatus object
            # so probably automatically by system
            download_control.visible_for_user = True
            download_control.status = 'OK'
            download_control.save()
            continue
        else:
            download_control.status = '?'
            # invisible to the the user when first generated by the admin
            download_control.visible_for_user = not is_contest_basicadmin(request)
            download_control.save()

        test_ids.append(testreport.test_id)

    return test_ids


@enforce_condition(contest_exists & can_enter_contest)
@require_POST
def generate_user_output_view(request, testreport_id=None, submission_report_id=None):
    """Prepares re-submission for generating user outputs and runs judging.

    If there are no test reports' ids given as argument, then all tests from
    reports with the ``submission_report_id`` would be used for generating
    user outs. In that case ``submission_report_id`` is required.
    Note that it uses only tests without already generated outs.

    Also adjusts already generated outs visibility for users
    on tests originally generated by admin.
    """
    assert testreport_id or submission_report_id, _("Not enough information given")

    # taking test report with given id
    if testreport_id is not None:
        testreport = get_object_or_404(TestReport, id=testreport_id)

        if submission_report_id is not None:
            # testreport_id is not related to given submission_report_id
            if submission_report_id != testreport.submission_report_id:
                raise SuspiciousOperation
        else:
            submission_report_id = testreport.submission_report_id
        testreports = [testreport]
    # taking all test reports related to submission report
    elif submission_report_id is not None:
        testreports = TestReport.objects.filter(
            submission_report__id=submission_report_id
        )

    # check download out permission
    submission_report = get_object_or_404(SubmissionReport, id=submission_report_id)
    _check_generate_out_permission(request, submission_report)

    # filtering tests for judge
    test_ids = _testreports_to_generate_outs(request, testreports)

    # creating re-submission with appropriate tests
    s_id = submission_report.submission_id
    submission = get_submission_or_error(
        request, s_id, submission_class=ProgramSubmission
    )
    if test_ids:
        # Note that submission comment should not be copied to re-submission!
        # It will be overwritten in handler anyway.
        resubmission = ProgramSubmission(
            problem_instance=submission.problem_instance,
            user=request.user,
            date=request.timestamp,
            kind='USER_OUTS',
            source_file=submission.source_file,
        )
        resubmission.save()
        resubmission.problem_instance.controller.judge(
            resubmission,
            extra_args={
                'tests_subset': test_ids,
                'submission_report_id': submission_report.id,
            },
        )

    return redirect(
        'submission', contest_id=request.contest.id, submission_id=submission.id
    )


@jsonify
def get_compiler_hints_view(request):
    language = request.GET.get('language', '')
    available_compilers = getattr(settings, 'AVAILABLE_COMPILERS', {})
    return list(available_compilers.get(language, {}).keys())


@jsonify
@enforce_condition(~contest_exists | can_enter_contest)
def get_language_hints_view(request):
    pi_ids = request.GET.getlist(u'pi_ids[]')
    filename = request.GET.get(u'filename', u'')
    pis = ProblemInstance.objects.filter(id__in=pi_ids)

    extension = get_extension(filename)
    lang_dict = {pi: get_language_by_extension(pi, extension) for pi in pis}

    if contest_exists(request):
        submittable_pis = submittable_problem_instances(request)
        lang_dict = {
            pi: lang for (pi, lang) in lang_dict.items() if pi in submittable_pis
        }
    else:
        problemsite_key = request.GET.get(u'problemsite_key', u'')
        lang_dict = {
            pi: lang
            for (pi, lang) in lang_dict.items()
            if pi.problem.problemsite.url_key == problemsite_key
        }

    langs = get_submittable_languages()
    lang_display_dict = {
        pi.id: langs.get(lang, {'display_name': ''})['display_name']
        for (pi, lang) in lang_dict.items()
    }

    return lang_display_dict
