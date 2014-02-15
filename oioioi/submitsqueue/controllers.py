from oioioi.programs.controllers import ProgrammingContestController
from oioioi.submitsqueue.models import QueuedSubmit


class SubmitsQueueContestControllerMixin(object):
    def finalize_evaluation_environment(self, environ):
        super(SubmitsQueueContestControllerMixin, self).\
            finalize_evaluation_environment(environ)
        environ['recipe'].insert(0, (
                'mark_submission_in_progress',
                'oioioi.submitsqueue.handlers.mark_submission_in_progress'))
        if 'postpone_handlers' not in environ:
            environ['postpone_handlers'] = []
        environ['postpone_handlers'].append(('update_celery_task_id',
                'oioioi.submitsqueue.handlers.update_celery_task_id'))
        if 'error_handlers' not in environ:
            environ['error_handlers'] = []
        environ['error_handlers'].insert(0, (
                'remove_submission_on_error',
                'oioioi.submitsqueue.handlers.remove_submission_on_error'))

    def submission_queued(self, submission, async_result):
        super(SubmitsQueueContestControllerMixin, self).\
            submission_queued(submission, async_result)
        QueuedSubmit.objects.get_or_create(submission=submission,
                                           celery_task_id=async_result.id)

    def submission_unqueued(self, submission, job_id):
        super(SubmitsQueueContestControllerMixin, self).\
            submission_unqueued(submission, job_id)
        QueuedSubmit.objects.filter(submission=submission,
                                    celery_task_id=job_id).delete()


ProgrammingContestController.mix_in(SubmitsQueueContestControllerMixin)
