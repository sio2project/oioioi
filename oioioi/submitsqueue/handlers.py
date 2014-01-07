from celery.exceptions import Ignore

from oioioi.submitsqueue.models import QueuedSubmit
from oioioi.contests.models import Submission


def mark_submission_in_progress(env, **kwargs):
    try:
        submission = Submission.objects.get(id=env['submission_id'])
        qs, created = QueuedSubmit.objects.get_or_create(submission=submission,
                                                celery_task_id=env['job_id'])
        if qs.state == 'CANCELLED':
            qs.delete()
            raise Ignore
        qs.state = 'PROGRESS'
        qs.save()
    except QueuedSubmit.DoesNotExist:
        pass    # race condition occured, but there's not much we can do
                # the submit won't be marked as 'in progress', but otherwise,
                # it will be evaluated just fine
    return env


def update_celery_task_id(env, **kwargs):
    try:
        qs = QueuedSubmit.objects.get(celery_task_id=env['job_id'])
        qs.celery_task_id = kwargs['async_result'].id
        qs.save()
    except QueuedSubmit.DoesNotExist:
        pass    # same as above
    return env


def remove_submission_on_error(env, **kwargs):
    try:
        qs = QueuedSubmit.objects.get(celery_task_id=env['job_id'])
        qs.delete()
    except QueuedSubmit.DoesNotExist:
        pass    # same as above
    return env
