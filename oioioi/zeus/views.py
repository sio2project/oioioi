import json
import logging
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from oioioi.zeus.backends import _get_key, _json_base64_decode
from oioioi.zeus.models import ZeusAsyncJob
from oioioi.zeus.utils import verify_zeus_url_signature
from oioioi.evalmgr.handlers import postpone

logger = logging.getLogger(__name__)


# View for use as Zeus callback

@csrf_exempt
@require_POST
def push_grade(request, check_uid, signature):
    # TODO: might use some kind of url signing decorator and skip
    # arguments from url
    if not verify_zeus_url_signature(check_uid, signature):
        raise PermissionDenied

    # This message may be useful for debugging in case when decoding fails
    logger.info('BEFORE DECODING BODY')
    body = _json_base64_decode(request.body)
    logger.info(' >>>> ')
    logger.info(body)
    logger.info(' <<<< ')

    if 'compilation_output' in body:
        compilation_result = 'CE'
    else:
        compilation_result = 'OK'


    if compilation_result == 'OK':
        reports = _get_key(body, 'tests_info')
    else:
        reports = []

    try:
        async_job, created = ZeusAsyncJob.objects.select_for_update() \
                             .get_or_create(check_uid=check_uid)
    except IntegrityError:
        # This should never happen.
        logger.error("IntegrityError while saving results for %s",
                     check_uid, exc_info=True)
        logger.error("Received reports:\n%s", reports)
        return HttpResponse("Recorded!")

    if async_job.resumed:
        logger.debug("Got results for %s again, ignoring", check_uid)
        return HttpResponse("Recorded!")

    if not created:
        logger.info("Resuming job %s", check_uid)
        env = json.loads(async_job.environ)
        env.setdefault('zeus_results', [])
        env['compilation_result'] = compilation_result
        env['compilation_message'] = body.get('compilation_output', '')
        env['zeus_results'].extend(list(reports))
        postpone(env)
        async_job.environ = json.dumps(env)
        async_job.resumed = True
        async_job.save()
    else:
        # The code below solves a race condition in case Zeus
        # does the callback before ZeusAsyncJob is created in handlers.
        async_job.environ = json.dumps({'zeus_results': list(reports)})
        async_job.save()

    # TODO: return a brief text response in a case of a failure
    # (Internal Server Error or Permission Denied).
    # Currently we respond with the default human-readable HTML.
    return HttpResponse("Recorded!")
