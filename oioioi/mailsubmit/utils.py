import hashlib
import hmac

from django.conf import settings

from oioioi.base.permissions import make_request_condition
from oioioi.base.utils import request_cached
from oioioi.contests.models import ProblemInstance
from oioioi.default_settings import MAILSUBMIT_CONFIRMATION_HASH_LENGTH
from oioioi.mailsubmit.models import MailSubmissionConfig


@make_request_condition
def is_mailsubmit_used(request):
    try:

        _msc = request.contest.mail_submission_config
        return True
    except MailSubmissionConfig.DoesNotExist:
        return False


@make_request_condition
def is_mailsubmit_allowed(request):
    try:
        msc = request.contest.mail_submission_config
        return (
            msc.enabled
            and msc.start_date is not None
            and msc.start_date <= request.timestamp
            and (msc.end_date is None or request.timestamp < msc.end_date)
        )
    except MailSubmissionConfig.DoesNotExist:
        return False


@make_request_condition
@request_cached
def has_any_mailsubmittable_problem(request):
    return bool(mailsubmittable_problem_instances(request))


@request_cached
def mailsubmittable_problem_instances(request):
    controller = request.contest.controller
    queryset = (
        ProblemInstance.objects.filter(contest=request.contest)
        .select_related('problem')
        .prefetch_related('round')
    )
    return [
        pi
        for pi in queryset
        if controller.can_submit(request, pi, check_round_times=False)
    ]


def accept_mail_submission(request, mailsubmission):
    ccontroller = request.contest.controller
    submission = ccontroller.create_submission(
        request,
        mailsubmission.problem_instance,
        {
            'user': mailsubmission.user,
            'file': mailsubmission.source_file,
            'kind': 'NORMAL',
        },
    )
    mailsubmission.submission = submission
    mailsubmission.accepted_by = request.user
    mailsubmission.save()
    return submission


def mail_submission_hashes(mailsubmission):
    source_hash = hashlib.sha256()
    for chunk in mailsubmission.source_file.chunks():
        source_hash.update(chunk)
    source_hash = source_hash.hexdigest()
    mailsubmission.source_file.seek(0)

    pi = mailsubmission.problem_instance

    msg = '%d-%s-%d-%s' % (mailsubmission.id, pi.contest.id, pi.id, source_hash)
    msg = msg.encode('utf-8')

    submission_hash = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        msg,
        'sha256'  # Name of the hashing algorithm is required from Python3.8.
    ).hexdigest()[:MAILSUBMIT_CONFIRMATION_HASH_LENGTH]

    return source_hash, submission_hash
