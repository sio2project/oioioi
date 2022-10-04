import copy
import pprint
import sys
from uuid import uuid4

import six
from celery.exceptions import Ignore
from celery import shared_task
from django.db import transaction
from django.utils.module_loading import import_string

from oioioi.base.utils.db import require_transaction
from oioioi.base.utils.loaders import load_modules
from oioioi.evalmgr import logger
from oioioi.evalmgr.models import QueuedJob, SavedEnviron
from oioioi.evalmgr.utils import mark_job_state

loaded_controllers = False


def _placeholder(environ, **kwargs):
    return environ


def _find_placeholder(recipe, name):
    placeholder = 'oioioi.evalmgr.tasks._placeholder'
    for i, entry in enumerate(recipe):
        if entry[0] == name and entry[1] == placeholder:
            return i
    raise IndexError("Placeholder '%s' not found in recipe" % (name,))


def find_recipe_entry(recipe, name):
    for i, entry in enumerate(recipe):
        if entry[0] == name:
            return i
    raise IndexError("Entry '%s' not found in recipe" % (name,))


def recipe_placeholder(name):
    return (name, 'oioioi.evalmgr.tasks._placeholder')


def create_environ():
    """Creates new environ, filling most basic fields. This fields can't be
    overwritten (they can be extended, etc):
    - job_id
    - error_handlers
    """
    return {
        'job_id': uuid4().urn,
        'error_handlers': [
            (
                'remove_queuedjob_on_error',
                'oioioi.evalmgr.handlers.remove_queuedjob_on_error',
            )
        ],
    }


def transfer_job(environ, transfer_func, restore_func, transfer_kwargs=None):
    """Transfers job to external evaluation system using given transfer
    function. Transfer function will be called with environ as first
    positional argument and **transfer_kwargs as keyword arguments.

    Environ is saved by evalmgr right before transfer, so the transfer
    function may send out only the information needed for the external
    evaluation system.

    The transfer_func isn't called from a database transaction, and thus
    shouldn't use database (unless it makes a transaction on its own).

    To resume a job, ``delay_environ`` must be called with the resulting
    environment as the argument, which must contain ``saved_environ_id``.
    This field is added to the environ right before ``transfer_func`` is
    called (so it isn't included in environ saved in database, but is in
    one handled as argument to ``transfer_func``).

    When job is resumed, evalmgr searches for a matching SavedEnviron. If it
    finds any, environ is updated with the external evaluation results (the
    ``delay_environ``'s argument) like::

      environ = restore_func(saved_environ, results_environ).

    If it doesn't find any, job is considered already resumed and is
    ignored.

    For details see ``evalmgr_job`` and ``delay_environ``.
    """
    if 'transfer' in environ:
        raise RuntimeError(
            'Tried to transfer environ again, with {func}({args})'.format(
                func=transfer_func, args=repr(transfer_kwargs)
            )
        )
    environ['transfer'] = {
        'transfer_func': transfer_func,
        'transfer_kwargs': transfer_kwargs or {},
    }
    environ['restore_environ_func'] = restore_func
    return environ


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
    recipe[index + 1 : index + 1] = entries


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
        raise TypeError('Receipt element has length neither 2 nor 3: %r' % phase)
    if len(phase) == 2:
        kwargs = {}
    if len(phase) == 3:
        kwargs = phase[2].copy()
    if extra_kwargs:
        kwargs.update(extra_kwargs)
    handler_func = import_string(handlerName)
    env = handler_func(env, **kwargs)
    if env is None:
        raise RuntimeError(
            'Evaluation handler "%s" (%s) '
            'forgot to return the environment.' % (phaseName, handlerName)
        )
    return env


@require_transaction
def _resume_job(environ):
    """Restores saved environ, returns environ or None, when a matching
    SavedEnviron wasn't found.
    """
    saved_environ_id = environ.pop('saved_environ_id')
    saved_environ_object = SavedEnviron.objects.filter(
        id=saved_environ_id
    ).select_for_update()
    if not saved_environ_object.exists():
        logger.info(
            'Job with environ id %s already resumed, ignoring.', str(saved_environ_id)
        )
        return None
    saved_environ_object = saved_environ_object.get()
    saved_environ = saved_environ_object.load_environ()
    saved_environ_object.delete()
    environ = import_string(saved_environ.pop('restore_environ_func'))(
        saved_environ, environ
    )
    # There is no need for removing 'saved_environ_id' from merged environ,
    # as it wasn't saved in database.
    return environ


@transaction.atomic
def _job_finished(environ):
    QueuedJob.objects.filter(job_id=environ['job_id']).delete()
    return environ


def _transfer_job(environ, transfer_func, transfer_kwargs):
    with transaction.atomic():
        marked = mark_job_state(environ, 'WAITING')
        if marked:
            # Save without ``environ['transfer']`` or
            # ``environ['saved_environ_id']``.
            saved_environ = SavedEnviron.save_environ(environ)
            environ['saved_environ_id'] = saved_environ.id
    if not marked:
        raise Ignore
    try:
        import_string(transfer_func)(environ, **transfer_kwargs)
    # pylint: disable=broad-except
    except Exception:
        with transaction.atomic():
            SavedEnviron.objects.filter(id=environ.pop('saved_environ_id')).delete()
        raise
    return environ


def _mark_job_state(environ, state):
    with transaction.atomic():
        marked = mark_job_state(environ, state)
    if not marked:
        raise Ignore


def _run_error_handlers(env, exc_info):
    logger.debug(
        "Handling exception '%s' in job:\n%s",
        exc_info[0],
        pprint.pformat(env, indent=4),
    )
    error_handlers = env.get('error_handlers', [])
    try:
        for phase in error_handlers:
            env = _run_phase(env, phase, extra_kwargs=dict(exc_info=exc_info))
    # pylint: disable=broad-except
    except Exception:
        logger.error(
            "Exception occured in job's error handlers:\n%s",
            pprint.pformat(env, indent=4),
            exc_info=True,
        )
    if not env.get('ignore_errors'):
        logger.error(
            "Exception occured in job:\n%s",
            pprint.pformat(env, indent=4),
            exc_info=exc_info,
        )
        six.reraise(exc_info[0], exc_info[1], exc_info[2])
    return env


@require_transaction
def delay_environ(environ, **evalmgr_extra_args):
    """Inserts environ into evalmgr queue with marking it as queued, resuming
    it if it should be. Returns associated async result, or None when job
    was already resumed before (or was cancelled).

    Requires to be called from transaction.
    """
    if 'saved_environ_id' in environ:
        environ = _resume_job(environ)
        if environ is None:
            return None
    if not mark_job_state(environ, 'QUEUED'):
        return None
    async_result = evalmgr_job.apply_async((environ,), **evalmgr_extra_args)
    QueuedJob.objects.filter(job_id=environ['job_id']).update(
        celery_task_id=async_result.id
    )
    return async_result


@shared_task
def evalmgr_job(env):
    r"""Takes environment and evaluates it according to its recipe.

    To queue environment one shouldn't call ``evalmgr_job.apply_async``
    or ``evalmgr_job.delay`` directly. Use ``delay_environ`` instead.

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

     A job may be transferred to an external evaluation system using
     ``transfer_job``. A recipe handler which want to transfer job should
     return environ processed by ``transfer_job``, like::

       def prepare_transfer_handler(environ, **kwargs):
         do_some_important_stuff(environ, **kwargs)
         return transfer_job(environ,
                             'some.module.transfer_function',
                             'functions.that.merges.saved.env.and.result')

     If during any of the phases an exception other than Ignore is thrown,
     and ``env['error_handlers']`` is present (it should be in the same
     format as recipe), functions listed there are called with
     additional ``exc_info`` argument, which is the ``sys.exc_info()``
     triple. If any exceptions are thrown there, they are reported to
     the logs and ignored.

     If a celery.exceptions.Ignore is thrown, then execution of environment
     is stopped. One who does it is responsible for handling corresponding
     QueuedJob object.

     Returns environment (a processed copy of given environment).
    """

    # pylint: disable=global-statement,broad-except
    global loaded_controllers

    # load controllers to avoid late mix-ins to them
    if not loaded_controllers:
        load_modules('controllers')
        loaded_controllers = True

    env = copy.deepcopy(env)

    try:
        if 'job_id' not in env:
            raise RuntimeError('No job_id found in environ')
        if 'recipe' not in env:
            raise RuntimeError(
                'No recipe found in job environment. '
                'Did you forget to set environ["run_externally"]?'
            )
        if 'error' in env:
            raise RuntimeError(
                'Error from workers:\n%s\nTB:\n%s'
                % (env['error']['message'], env['error']['traceback'])
            )
        _mark_job_state(env, 'PROGRESS')
        while True:
            recipe = env.get('recipe')
            if not recipe:
                env = _job_finished(env)
                break
            phase = recipe[0]
            env['recipe'] = recipe[1:]
            env = _run_phase(env, phase)
            if 'transfer' in env:
                env = _transfer_job(env, **env.pop('transfer'))
                break
        return env

    # Throwing up celery.exceptions.Ignore is necessary for our custom revoke
    # mechanism. Basically, one of the handlers in job's recipe throws Ignore
    # if the submission had been revoked and this exception has to be passed
    # up so that celery recognizes it and stops execution of this job.
    except Ignore:
        raise
    # pylint: disable=broad-except
    except Exception:
        return _run_error_handlers(env, sys.exc_info())
