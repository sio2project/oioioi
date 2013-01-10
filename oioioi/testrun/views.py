from django.core.urlresolvers import reverse
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import redirect, get_object_or_404

from oioioi.base.menu import menu_registry
from oioioi.contests.utils import can_enter_contest
from oioioi.base.permissions import enforce_condition
from oioioi.contests.forms import SubmissionForm
from oioioi.testrun.models import TestRunProgramSubmission, TestRunReport
from oioioi.contests.views import check_submission_access
from oioioi.filetracker.utils import stream_file
from oioioi.testrun.utils import has_any_testrun_problem, \
    filter_testrun_problem_instances

menu_registry.register('testrun', _("Test run"),
        lambda request: reverse('testrun_submit', kwargs={'contest_id':
            request.contest.id}),
        condition=has_any_testrun_problem,
        order=300)

@enforce_condition(can_enter_contest)
@enforce_condition(has_any_testrun_problem)
def testrun_submit_view(request, contest_id):
    if request.method == 'POST':
        form = SubmissionForm(request, request.POST, request.FILES,
                kind='TESTRUN', problem_filter=filter_testrun_problem_instances)
        if form.is_valid():
            request.contest.controller.create_testrun(request,
                    form.cleaned_data['problem_instance'], form.cleaned_data)
            return redirect('my_submissions', contest_id=contest_id)
    else:
        form = SubmissionForm(request, kind='TESTRUN',
                                problem_filter=filter_testrun_problem_instances)
    return TemplateResponse(request, 'testrun/submit.html', {'form': form})

def get_submission_or_404(request, contest_id, submission_id):
    """Returns the submission if it exists and user has rights to see it."""
    submission = get_object_or_404(TestRunProgramSubmission, id=submission_id)
    if contest_id != submission.problem_instance.contest_id:
        raise Http404
    check_submission_access(request, submission)
    return submission

def get_preview_size_limit():
    return 1024;

@enforce_condition(can_enter_contest)
def show_input_file_view(request, contest_id, submission_id):
    submission = get_submission_or_404(request, contest_id, submission_id)

    try:
        data = submission.input_file.read(get_preview_size_limit()) \
                .decode('utf-8')
    except UnicodeDecodeError: #TODO: use alert-warning
        data = _("Error: can't display non ascii/utf8 file")

    size = submission.input_file.size
    return TemplateResponse(request, 'testrun/data.html', {
        'header': _("Input"),
        'data': data,
        'left': size - get_preview_size_limit(),
    })

@enforce_condition(can_enter_contest)
def download_input_file_view(request, contest_id, submission_id):
    submission = get_submission_or_404(request, contest_id, submission_id)

    return stream_file(submission.input_file, name='input.in')

@enforce_condition(can_enter_contest)
def show_output_file_view(request, contest_id, submission_id):
    submission = get_submission_or_404(request, contest_id, submission_id)
    result = get_object_or_404(TestRunReport,
                               submission_report__submission=submission,
                               submission_report__status='ACTIVE')

    try:
        data = result.output_file.read(get_preview_size_limit()).decode('utf-8')
    except UnicodeDecodeError:
        data = _("Error: can't display non ascii/utf8 file")

    size = result.output_file.size
    return TemplateResponse(request, 'testrun/data.html', {
        'header': _("Output"),
        'data': data,
        'left': size - get_preview_size_limit(),
    })

@enforce_condition(can_enter_contest)
def download_output_file_view(request, contest_id, submission_id):
    submission = get_submission_or_404(request, contest_id, submission_id)
    result = get_object_or_404(TestRunReport,
                               submission_report__submission=submission,
                               submission_report__status='ACTIVE')
    return stream_file(result.output_file, name='output.out')
