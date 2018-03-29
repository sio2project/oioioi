import logging

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from oioioi.evalmgr.tasks import delay_environ
from oioioi.zeus.backends import _get_key, _json_base64_decode
from oioioi.zeus.utils import verify_zeus_url_signature

logger = logging.getLogger(__name__)


# View for use as Zeus callback

@csrf_exempt
@require_POST
def push_grade(request, saved_environ_id, signature):
    # TODO: might use some kind of url signing decorator and skip
    # arguments from url
    if not verify_zeus_url_signature(saved_environ_id, signature):
        raise PermissionDenied

    # This message may be useful for debugging in case when decoding fails
    logger.info('BEFORE DECODING BODY')
    try:
        body = _json_base64_decode(request.body)
    except ValueError:
        logger.info('Invalid b64 JSON: %s', request.body)
        return HttpResponse(
            'Got invalid payload. It is not JSON with base64 strings.',
            status=400)
    logger.info(' >>>> ')
    logger.info(body)
    logger.info(' <<<< ')

    # Create a small ``env`` that will be used to resume the job. Actuall
    # results processing is done in oioioi.zeus.handlers.restore_job.
    env = {'saved_environ_id': saved_environ_id}
    if 'compilation_output' in body:
        env['compilation_result'] = 'CE'
        env['reports'] = []
    else:
        env['compilation_result'] = 'OK'
        env['reports'] = list(_get_key(body, 'tests_info'))
    env['compilation_message'] = body.get('compilation_output', '')

    delay_environ(env)
    return HttpResponse('Recorded!')
