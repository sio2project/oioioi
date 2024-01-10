import logging

from celery import shared_task
from django.utils.module_loading import import_string
from oioioi.problems.models import Problem, ProblemPackage

logger = logging.getLogger(__name__)


@shared_task
def unpackmgr_job(env):
    """Creates (or modifies) a :class:`~oioioi.problems.models.Problem`
    instance using a package file represented by a
    :class:`~oioioi.problems.models.ProblemPackage`.

    Used ``env`` keys:
      ``package_id``: id of the
      :class:`~oioioi.problems.models.ProblemPackage` instance to process

      ``backend_name``:
      problem package backend (dotted name) to be used for unpacking

      ``post_upload_handlers``: a list of handler functions to be called
      after the new problem is created

    Before the handlers are called, the following ``env`` keys are produced:

      ``job_id``: the ``Celery`` task id

      ``problem_id``: id of the
      :class:`~oioioi.problems.models.ProblemPackage` instance,
      which was created or modified
    """
    try:
        package = ProblemPackage.objects.get(id=env['package_id'])

        with package.save_operation_status():
            env['job_id'] = unpackmgr_job.request.id
            backend = import_string(env['backend_name'])()
            env = backend.unpack(env)
            ProblemPackage.objects.get(id=env['package_id'])
            problem = Problem.objects.get(id=env['problem_id'])
            package.celery_task_id = unpackmgr_job.request.id
            package.problem = problem
            package.save()

            for h in env['post_upload_handlers']:
                handler = import_string(h)
                env = handler(env)

    except ProblemPackage.DoesNotExist:
        logger.warning(
            "Problem package %s got deleted before it was processed.",
            env['package_id'],
        )
