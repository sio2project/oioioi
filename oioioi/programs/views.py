from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from oioioi.programs.models import ProgramSubmission, Test
from oioioi.contests.views import check_submission_access
from oioioi.contests.utils import enter_contest_permission_required
from oioioi.filetracker.utils import stream_file

@enter_contest_permission_required
def show_submission_source_view(request, contest_id, submission_id):
    submission = get_object_or_404(ProgramSubmission, id=submission_id)
    if contest_id != submission.problem_instance.contest_id:
        raise Http404
    check_submission_access(request, submission)
    response = HttpResponse(submission.source_file.read(),
            content_type='text/plain')
    response['Content-Disposition'] = 'inline'
    return response

@enter_contest_permission_required
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
