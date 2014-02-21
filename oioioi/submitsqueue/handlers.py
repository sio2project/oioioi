from celery.exceptions import Ignore
from django.db import transaction

from oioioi.submitsqueue.models import QueuedSubmit
from oioioi.contests.models import Submission


@transaction.commit_manually
def mark_submission_in_progress(env, **kwargs):
    try:
        submission = Submission.objects.get(id=env['submission_id'])
        qs, _created = QueuedSubmit.objects.get_or_create(
                submission=submission, celery_task_id=env['job_id'])

        if qs.state == 'CANCELLED':
            qs.delete()
            raise Ignore
        qs.state = 'PROGRESS'
        qs.save()
    finally:
        transaction.commit()
    return env


@transaction.commit_on_success
def update_celery_task_id(env, **kwargs):
    try:
        qs = QueuedSubmit.objects.get(celery_task_id=env['job_id'])
        qs.celery_task_id = kwargs['async_result'].id
        qs.save()
    except QueuedSubmit.DoesNotExist:
        pass    # Submission already judged.
    return env


@transaction.commit_on_success
def remove_submission_on_error(env, **kwargs):
    QueuedSubmit.objects.filter(celery_task_id=env['job_id']).delete()
    return env
