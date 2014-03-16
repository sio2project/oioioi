from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import redirect, get_object_or_404

from oioioi.base.menu import menu_registry
from oioioi.contests.utils import can_enter_contest, is_contest_admin, \
    contest_exists, get_submission_or_error
from oioioi.base.permissions import enforce_condition
from oioioi.contests.forms import SubmissionForm
from oioioi.programs.utils import decode_str
from oioioi.testrun.models import TestRunProgramSubmission, TestRunReport
from oioioi.filetracker.utils import stream_file
from oioioi.testrun.utils import has_any_testrun_problem, \
    filter_testrun_problem_instances


@menu_registry.register_decorator(_("Test run"), lambda request:
    reverse('testrun_submit', kwargs={'contest_id':
            request.contest.id}),
    order=300)
@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(has_any_testrun_problem,
                   template='testrun/no_testrun_problems.html')
def testrun_submit_view(request, contest_id):
    if request.method == 'POST':
        form = SubmissionForm(request, request.POST, request.FILES,
                kind='TESTRUN',
                problem_filter=filter_testrun_problem_instances)
        if form.is_valid():
            request.contest.controller.create_testrun(request,
                    form.cleaned_data['problem_instance'], form.cleaned_data)
            return redirect('my_submissions', contest_id=contest_id)
    else:
        form = SubmissionForm(request, kind='TESTRUN',
                              problem_filter=filter_testrun_problem_instances)
    return TemplateResponse(request, 'testrun/submit.html', {'form': form})


def get_preview_size_limit():
    return 1024


def get_testrun_report_or_404(request, submission, testrun_report_id=None,
        model=TestRunReport):
    qs = model.objects.filter(submission_report__submission=submission)

    if is_contest_admin(request) and testrun_report_id is not None:
        qs = qs.filter(id=testrun_report_id)
    else:
        qs = qs.filter(submission_report__status='ACTIVE')

    return get_object_or_404(qs)


@enforce_condition(contest_exists & can_enter_contest)
def show_input_file_view(request, contest_id, submission_id):
    submission = get_submission_or_error(request, contest_id, submission_id,
                                         TestRunProgramSubmission)
    data = submission.input_file.read(get_preview_size_limit())
    data, decode_error = decode_str(data)
    size = submission.input_file.size
    download_url = reverse('download_testrun_input',
            kwargs={'contest_id': request.contest.id,
                    'submission_id': submission_id})
    return TemplateResponse(request, 'testrun/data.html', {
        'header': _("Input"),
        'data': data,
        'left': size - get_preview_size_limit(),
        'decode_error': decode_error,
        'download_url': download_url
    })


@enforce_condition(contest_exists & can_enter_contest)
def download_input_file_view(request, contest_id, submission_id):
    submission = get_submission_or_error(request, contest_id, submission_id,
                                         TestRunProgramSubmission)

    return stream_file(submission.input_file, name='input.in')


@enforce_condition(contest_exists & can_enter_contest)
def show_output_file_view(request, contest_id, submission_id,
                          testrun_report_id=None):
    submission = get_submission_or_error(request, contest_id, submission_id,
                                         TestRunProgramSubmission)
    result = get_testrun_report_or_404(request, submission, testrun_report_id)
    data = result.output_file.read(get_preview_size_limit())
    data, decode_error = decode_str(data)
    size = result.output_file.size
    download_url = reverse('download_testrun_output',
            kwargs={'contest_id': request.contest.id,
                    'submission_id': submission_id})
    return TemplateResponse(request, 'testrun/data.html', {
        'header': _("Output"),
        'data': data,
        'left': size - get_preview_size_limit(),
        'decode_error': decode_error,
        'download_url': download_url
    })


@enforce_condition(contest_exists & can_enter_contest)
def download_output_file_view(request, contest_id, submission_id,
                              testrun_report_id=None):
    submission = get_submission_or_error(request, contest_id, submission_id,
                                         TestRunProgramSubmission)
    result = get_testrun_report_or_404(request, submission, testrun_report_id)
    return stream_file(result.output_file, name='output.out')
