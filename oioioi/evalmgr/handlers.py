from oioioi import evalmgr
import copy
import logging
import pprint

logger = logging.getLogger(__name__)

def postpone(env, **extra_args):
    saved_env = copy.copy(env)
    env['recipe'] = []
    logger.debug('Postponing evaluation of %(env)r', {'env': saved_env})
    evalmgr.evalmgr_job.apply_async((saved_env,), **extra_args)
    return env

def error_handled(env, **kwargs):
    env['ignore_errors'] = True
    return env

def dump_env(env, message, **kwargs):
    logger.debug(message + ":\n%s", pprint.pformat(env, indent=4))
    return env

