import logging
import pprint

from django.db import transaction

from oioioi.evalmgr.models import QueuedJob

logger = logging.getLogger(__name__)


def error_handled(env, **kwargs):
    env["ignore_errors"] = True
    return env


def dump_env(env, message, **kwargs):
    logger.debug(message + ":\n%s", pprint.pformat(env, indent=4))
    return env


@transaction.atomic
def remove_queuedjob_on_error(environ, **kwargs):
    QueuedJob.objects.filter(job_id=environ["job_id"]).delete()
    return environ
