import os
import random
import string

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.views.decorators.http import require_POST

from oioioi.base.utils import jsonify
from oioioi.contests.forms import SubmissionForm
from oioioi.submitservice.models import SubmitServiceToken
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.contests.utils import contest_exists, can_enter_contest, \
        visible_problem_instances


class SubmitServiceException(Exception):
    pass


def match_problem(problem_instances, problem):
    problem_id = None
    for pi in problem_instances:
        if pi.short_name == problem:
            return pi
        elif pi.short_name.find(problem) != -1:
            if problem_id is None:
                problem_id = pi
            else:
                # matched more than one available problem
                return None
    return problem_id


@jsonify
@csrf_exempt
@require_POST
@enforce_condition(contest_exists)
def submit_view(request):
    try:
        token = request.POST['token']
        current_token = SubmitServiceToken.objects.filter(token=token)
        if not current_token.exists():
            raise PermissionDenied('AUTHORIZATION_FAILED')
        request.user = current_token[0].user
        if not can_enter_contest(request):
            raise PermissionDenied('AUTHORIZATION_FAILED')
        task_name = request.POST['task']
        file_name, file_extension = \
            os.path.splitext(request.FILES['file'].name)
        if task_name:
            file_name = task_name
        pi = match_problem(visible_problem_instances(request), file_name)
        if not pi:
            raise SubmitServiceException('NO_SUCH_PROBLEM', ', '.join([
                    x.short_name for x in visible_problem_instances(request)]))

        lang_exts = sum(
            getattr(settings, 'SUBMITTABLE_EXTENSIONS', {}).values(), [])
        if file_extension[1:] not in lang_exts:
            raise ValueError('UNSUPPORTED_EXTENSION')

        form = SubmissionForm(request, {
            'problem_instance_id': pi.id,
            'user': request.user,
            'kind': 'NORMAL'
        }, request.FILES)
        if not form.is_valid():
            raise SubmitServiceException('INVALID_SUBMISSION', form.errors)
        submission = request.contest.controller \
            .create_submission(request, pi, form.cleaned_data)
        result_url = reverse('oioioi.contests.views.submission_view',
                                kwargs={'contest_id': request.contest.id,
                                'submission_id': submission.id})
        result = {'result_url': result_url, 'submission_id': submission.id}
    except SubmitServiceException as exception_info:
        result = {'error_code': exception_info.args[0],
                  'error_data': exception_info.args[1]
                  if len(exception_info.args) == 2 else ''}
    except StandardError as e:
        result = {'error_code': 'UNKNOWN_ERROR',
                  'error_data': str(e)}
    return result


@enforce_condition(not_anonymous & contest_exists)
def view_user_token(request):
    current_token = SubmitServiceToken.objects.filter(user=request.user)
    if not current_token.exists():
        current_token = SubmitServiceToken()
        current_token.token = generate_token()
        current_token.user = request.user
        current_token.save()
    else:
        current_token = current_token[0]
    return TemplateResponse(request, 'submitservice/view-user-token.html',
                            {'token': current_token.token,
                             'contest_url': request.build_absolute_uri(reverse(
                                 'oioioi.contests.views.default_contest_view',
                                 kwargs={'contest_id': request.contest.id}))
                             })


def generate_token():
    new_token = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for _ in range(32))
    # It is very improbable, but it could happen that the generated token
    # is already present in the dictionary. Let's generate new one.
    if SubmitServiceToken.objects.filter(token=new_token).exists():
        return generate_token()
    return new_token


@enforce_condition(not_anonymous & contest_exists)
@require_POST
def clear_user_token(request):
    current_token = SubmitServiceToken.objects.filter(user=request.user)
    if current_token.exists():
        current_token.delete()
    return redirect(reverse('submitservice_view_user_token',
                     kwargs={'contest_id': request.contest.id}))
