# pylint: disable=W0703
# Catching too general exception Exception
import copy
import sys
import logging
import pprint
import traceback

from celery.task import task
from celery.exceptions import Ignore

from oioioi.base.utils import get_object_by_dotted_name
from oioioi.base.utils.loaders import load_modules


logger = logging.getLogger(__name__)
loaded_controllers = False


def _placeholder(environ, **kwargs):
    return environ


def _find_placeholder(recipe, name):
    for i, entry in enumerate(recipe):
        if entry[0] == name and entry[1] == 'oioioi.evalmgr._placeholder':
            return i
    raise IndexError("Placeholder '%s' not found in recipe" % (name,))


def find_recipe_entry(recipe, name):
    for i, entry in enumerate(recipe):
        if entry[0] == name:
            return i
    raise IndexError("Entry '%s' not found in recipe" % (name,))


def recipe_placeholder(name):
    return (name, 'oioioi.evalmgr._placeholder')


def add_after_placeholder(environ, name, entry):
    recipe = environ['recipe']
    index = _find_placeholder(recipe, name)
    recipe.insert(index + 1, entry)


def add_before_placeholder(environ, name, entry):
    recipe = environ['recipe']
    index = _find_placeholder(recipe, name)
    recipe.insert(index, entry)


def extend_after_placeholder(environ, name, entries):
    recipe = environ['recipe']
    index = _find_placeholder(recipe, name)
    recipe[index + 1:index + 1] = entries


def extend_before_placeholder(environ, name, entries):
    recipe = environ['recipe']
    index = _find_placeholder(recipe, name)
    recipe[index:index] = entries


def add_after_recipe_entry(environ, name, entry):
    recipe = environ['recipe']
    index = find_recipe_entry(recipe, name)
    recipe.insert(index + 1, entry)


def add_before_recipe_entry(environ, name, entry):
    recipe = environ['recipe']
    index = find_recipe_entry(recipe, name)
    recipe.insert(index, entry)


def replace_recipe_entry(environ, name, new_entry):
    recipe = environ['recipe']
    index = find_recipe_entry(recipe, name)
    recipe[index] = new_entry


def _run_phase(env, phase, extra_kwargs=None):
    phaseName = phase[0]
    handlerName = phase[1]
    if len(phase) not in [2, 3]:
        raise TypeError('Receipt element has length neither 2 nor 3: %r'
                % phase)
    if len(phase) == 2:
        kwargs = {}
    if len(phase) == 3:
        kwargs = phase[2].copy()
    if extra_kwargs:
        kwargs.update(extra_kwargs)
    handler_func = get_object_by_dotted_name(handlerName)
    env = handler_func(env, **kwargs)
    if env is None:
        raise RuntimeError('Evaluation handler "%s" (%s) '
            'forgot to return the environment.' % (phaseName,
            handlerName))
    return env


def _run_error_handlers(env, exc_info):
    logger.debug("Handling exception '%s' in job:\n%s",
            exc_info[0], pprint.pformat(env, indent=4))
    error_handlers = env.get('error_handlers', [])
    try:
        for phase in error_handlers:
            env = _run_phase(env, phase, extra_kwargs=dict(exc_info=exc_info))
    except Exception:
        logger.error("Exception occured in job's error handlers:\n%s",
                pprint.pformat(env, indent=4), exc_info=True)
    if not env.get('ignore_errors'):
        logger.error("Exception occured in job:\n%s",
                pprint.pformat(env, indent=4), exc_info=exc_info)
        raise exc_info[0], exc_info[1], exc_info[2]
    return env


def _run_evaluation_postponed_handlers(async_result, saved_env):
    handlers = saved_env.get('postpone_handlers', [])
    for phase in handlers:
        try:
            saved_env = _run_phase(saved_env, phase,
                    extra_kwargs=dict(async_result=async_result))
        except Exception:
            # we cannot really handle the exception in any other way than
            # logging
            logger.error(
                    'postpone: evaluation_postponed threw an exception:\n %s',
                    traceback.format_exc())


@task
def evalmgr_job(env):
    r"""Takes environment and evaluates it according to its recipe.

       It needs some env elements to be set:

        ``env['recipe']`` should be a list of tuples
            (``phaseName``, ``handler_fun`` [, ``kwargs``])

            handler_fun should satisfy this definition:
                def handler_fun(``env``, ``\*\*kwargs``):

            kwargs will be passed to ``handler_fun``

            current environment would be passed as ``env``

        It's guaranteed that handler functions would be run in order they're
        listed and that environment modified by previous function will be
        passed to next function unchanged.

        Before running the job, its unique identifier is generated and saved in
        ``env['job_id']``.

        If during any of the phases an exception is thrown, and
        ``env['error_handlers']`` is present (it should be in the same
        format as recipe), functions listed there are called with
        additional ``exc_info`` argument, which is the ``sys.exc_info()``
        triple. If any exceptions are thrown there, they are reported to
        the logs and ignored.

        Returns environment (a processed copy of given environment).
    """

    # pylint: disable=global-statement
    global loaded_controllers

    # load controllers to avoid late mix-ins to them
    if not loaded_controllers:
        load_modules('controllers')
        loaded_controllers = True

    env = copy.deepcopy(env)
    env['job_id'] = evalmgr_job.request.id

    try:
        if 'recipe' not in env:
            raise RuntimeError('No recipe found in job environment. '
                    'Did you forget to set environ["run_externally"]?')

        while True:
            recipe = env.get('recipe')
            if not recipe:
                break
            phase = recipe[0]
            env['recipe'] = recipe[1:]
            env = _run_phase(env, phase)

        return env

    # Throwing up celery.exceptions.Ignore is necessary for our custom revoke
    # mechanism. Basically, one of the handlers in job's recipe throws Ignore
    # if the submission had been revoked and this exception has to be passed
    # up so that celery recognizes it and stops execution of this job.
    except Ignore:
        raise
    except Exception:
        return _run_error_handlers(env, sys.exc_info())
