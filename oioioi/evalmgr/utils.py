import logging

import six

from oioioi.base.utils.db import require_transaction
from oioioi.contests.models import Submission
from oioioi.evalmgr.models import QueuedJob

logger = logging.getLogger(__name__)


@require_transaction
def mark_job_state(environ, state, **kwargs):
    """Sets status of given environ in job queue. Additional arguments are
    used to update QueuedJob object. Returns True when the status was
    set, and the job should be continued, False when it ought to be
    ignored.
    """
    if 'submission_id' in environ:
        submission = Submission.objects.filter(id=environ['submission_id'])
        if submission.exists():
            kwargs['submission'] = submission.get()
    kwargs['state'] = state
    qj, created = QueuedJob.objects.get_or_create(
        job_id=environ['job_id'], defaults=kwargs
    )
    if not created:
        if qj.state == 'CANCELLED':
            qj.delete()
            logger.info('Job %s cancelled.', str(environ['job_id']))
            return False
        else:
            for k, v in six.iteritems(kwargs):
                setattr(qj, k, v)
            qj.save()
    return True
