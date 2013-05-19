import json
from datetime import timedelta

from django.http import HttpResponse, HttpResponseServerError
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_exempt
from oioioi.base.permissions import enforce_condition
from oioioi.contests.models import Submission
from oioioi.contests.utils import can_enter_contest, contest_exists
from oioioi.oisubmit.forms import OISubmitSubmissionForm
from oioioi.oisubmit.models import OISubmitExtraData
from oioioi.oisubmit.err_dict import INCORRECT_FORM_COMMENTS, SUSPICION_REASONS

def oisubmit_response(error_occured, comment):
    response = dict(error_occured=error_occured, comment=comment)
    return HttpResponse(json.dumps(response), content_type='application/json')

@csrf_exempt
@enforce_condition(contest_exists & can_enter_contest)
def oisubmit_view(request, contest_id):
    if request.method == 'POST':
        form = OISubmitSubmissionForm(request, request.POST, request.FILES)
        if form.is_valid():
            # Dates are interpreted as local timezone.
            if form.cleaned_data.get('siotime', None) is not None:
                submission_date = form.cleaned_data['siotime']
            elif form.cleaned_data.get('localtime', None) is not None:
                submission_date = form.cleaned_data['localtime']
            else:
                return HttpResponseServerError("Localtime is None")

            servertime = request.timestamp
            request.timestamp = submission_date
            pi = form.cleaned_data['problem_instance']

            task_submission_no = Submission.objects \
                .filter(user=request.user, problem_instance__id=pi.id) \
                .filter(kind=form.cleaned_data['kind']) \
                .count() + 1

            submissions_limit = \
                request.contest.controller.get_submissions_limit(request, pi)

            errors = []

            if submissions_limit and task_submission_no > submissions_limit:
                errors.append('SLE')

            rt = request.contest.controller.get_round_times(request, pi.round)

            if rt.is_future(request.timestamp):
                errors.append('BEFORE_START')
            if rt.is_past(request.timestamp):
                errors.append('AFTER_END')

            if abs(request.timestamp - servertime) >= timedelta(seconds=30):
                errors.append('TIMES_DIFFER')

            err_msg = ','.join(errors)

            received_suspected = bool(errors)
            if(received_suspected):
                form.cleaned_data['kind'] = 'SUSPECTED'

            submission = request.contest.controller.create_submission(request,
                    pi, form.cleaned_data, judge_after_create = not(errors))

            extra_data = OISubmitExtraData(submission=submission,
                                localtime = form.cleaned_data['localtime'],
                                siotime = form.cleaned_data['siotime'],
                                servertime = servertime,
                                received_suspected = received_suspected,
                                comments = err_msg)
            extra_data.save()

            if errors:
                msg = '\n'.join(unicode(SUSPICION_REASONS[err]) for err
                                in errors if err in SUSPICION_REASONS)
                return oisubmit_response(True, msg)
            else:
                msg = submission_date.strftime("%Y-%m-%d %H:%M:%S")
                return oisubmit_response(False, unicode(msg))
        else:
            if form.errors.keys()[0] in INCORRECT_FORM_COMMENTS:
                msg = INCORRECT_FORM_COMMENTS[form.errors.keys()[0]]
            else:
                msg = form.errors.values()[0].as_text()
            return oisubmit_response(True, unicode(msg))
    else:
        form = OISubmitSubmissionForm(request)
    return TemplateResponse(request, 'contests/submit.html', {'form': form})
