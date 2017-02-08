import copy
import logging
import pprint

from oioioi import evalmgr


logger = logging.getLogger(__name__)


def postpone(env, **extra_args):
    saved_env = copy.copy(env)
    env['recipe'] = []
    logger.debug('Postponing evaluation of %(env)r', {'env': saved_env})
    async_result = evalmgr.evalmgr_job.apply_async((saved_env,), **extra_args)
    if 'evalmgr_extra_args' in env:
        extra_args.update(env['evalmgr_extra_args'])
    evalmgr._run_evaluation_postponed_handlers(async_result, saved_env)
    return env


def error_handled(env, **kwargs):
    env['ignore_errors'] = True
    return env


def dump_env(env, message, **kwargs):
    logger.debug(message + ":\n%s", pprint.pformat(env, indent=4))
    return env
