from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.permissions import enforce_condition
from oioioi.contests.utils import get_submission_or_error, can_enter_contest, \
        contest_exists
from oioioi.filetracker.utils import stream_file
from oioioi.programs.utils import decode_str
from oioioi.testrun.views import get_testrun_report_or_404, get_preview_size_limit
from oioioi.zeus.backends import get_zeus_server
from oioioi.zeus.models import ZeusTestRunProgramSubmission, ZeusTestRunReport


@enforce_condition(contest_exists & can_enter_contest)
def show_library_file_view(request, contest_id, submission_id):
    submission = get_submission_or_error(request, contest_id, submission_id,
            ZeusTestRunProgramSubmission)
    data = submission.library_file.read(get_preview_size_limit())
    data, decode_error = decode_str(data)
    size = submission.library_file.size
    download_url = reverse('zeus_download_testrun_library',
        kwargs={'contest_id': request.contest.id,
                'submission_id': submission_id})
    return TemplateResponse(request, 'testrun/data.html', {
        'header': _("Library"),
        'data': data,
        'left': size - get_preview_size_limit(),
        'decode_error': decode_error,
        'download_url': download_url
    })


@enforce_condition(contest_exists & can_enter_contest)
def download_library_file_view(request, contest_id, submission_id):
    submission = get_submission_or_error(request, contest_id, submission_id,
            ZeusTestRunProgramSubmission)

    # TODO: filename
    return stream_file(submission.library_file, name='lib.h')


@enforce_condition(contest_exists & can_enter_contest)
def show_output_file_view(request, contest_id, submission_id,
        testrun_report_id=None):
    submission = get_submission_or_error(request, contest_id, submission_id,
            ZeusTestRunProgramSubmission)
    result = get_testrun_report_or_404(request, submission, testrun_report_id,
            ZeusTestRunReport)
    data = result.output_file.read(get_preview_size_limit())
    data, decode_error = decode_str(data)
    size = result.full_out_size
    download_url = reverse('zeus_download_testrun_output',
        kwargs={'contest_id': request.contest.id,
                'submission_id': submission_id})
    return TemplateResponse(request, 'testrun/data.html', {
        'header': _("Output"),
        'data': data,
        'left': size - len(data),
        'decode_error': decode_error,
        'download_url': download_url
    })


@enforce_condition(contest_exists & can_enter_contest)
def download_output_file_view(request, contest_id, submission_id,
        testrun_report_id=None):
    submission = get_submission_or_error(request, contest_id, submission_id,
            ZeusTestRunProgramSubmission)
    result = get_testrun_report_or_404(request, submission, testrun_report_id,
            ZeusTestRunReport)

    if result.output_file.size != result.full_out_size:
        zeus_server = get_zeus_server(
                submission.problem_instance.problem.zeusproblemdata.zeus_id)
        file = zeus_server.download_output(int(result.full_out_handle))
        result.output_file.save('full_out', ContentFile(file))

    return stream_file(result.output_file, name='output.out')
