=====================
Submission evaluation
=====================

TODO

Evaluation manager vs workers
-----------------------------

TODO

Running evaluation manager jobs
-------------------------------

An `Environment` is a dict which contains all data necessary to complete
a `Job` and describes how to do it. An `Environment['recipe']` contains a list
of functions (`Handlers`) which need to be called to do the work.

A `Handler` is a function like this::

  def handler(environ, **kwargs):
      # ... do something ...
      return modified_environ

The `Handler` simply gets the `Environment`
(and optionally -- additional args specified in `Environment['recipe']`
) and returns a modified `Environment`, which is then passed to the next
handler, and so on.

Therefore each `Handler` does some work (e.g. runs tests, judges tests,
compiles a program...) based on the `Environment` state and saves the results
into it.

Modifying recipe inside handlers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TODO

Running workers jobs
--------------------

TODO

.. _workers:

Workers reference
^^^^^^^^^^^^^^^^^

Code which actually runs on the judging machines (compilation, safe execution
etc.) is not part of the OIOIOI Django project.  It lives in ``sioworkers``
subfolder in the Git tree.

.. _Evaluation workers: ../../../../../sioworkers/sio-workers/rst/build/html/index.html
.. _Workers-Celery bindings: ../../../../../sioworkers/sio-celery/rst/build/html/index.html
.. _Compilation jobs: ../../../../../sioworkers/sio-compilers/rst/build/html/index.html
.. _Safe execution jobs: ../../../../../sioworkers/sio-exec/rst/build/html/index.html

Have a look at an overview in the `Evaluation workers`_ document.

See also:

- `Workers-Celery bindings`_ (``sio.celery`` module)
- `Compilation jobs`_ (``sio.compilers`` module)
- `Safe execution jobs`_ (``sio.exec`` module)



Environment for submission evaluation
-------------------------------------

The evaluation environment is created when a new submission arrives or a
rejudge request is received. The environment is built by
:meth:`~oioioi.contests.controllers.ContestController.build_evaluation_environ`.

.. automethod:: oioioi.contests.controllers.ContestController.build_evaluation_environ
    :noindex:

What's in the environment?
^^^^^^^^^^^^^^^^^^^^^^^^^^

``recipe``
  a list of tuples in form of ``[ (handler_name, handler_path, [kwargs]),
  ...]``, where:

  * ``handler_name`` is a unique identifier of the  `Handler` in the
    ``recipe``,

  * ``hander_path`` is a :term:`dotted name` of the `Handler` function,

  * ``kwargs`` is an optional dictionary of additional arguments for the
    `Handler`.

``error_handlers``
  a list of tuples in the same form as the ``recipe`` content,  which will be
  used as a job recipe for main recipe error handling; each error handler
  should take a special argument called `exc_info`, which contains exception
  related information obtained by :func:`sys.exc_info()` ::

    def sample_error_handler(env, exc_info, **kwargs):
        logger.error(exc_info[1])

``ignore_errors``
  a boolean, which indicates if errors during an evaluation should stop job
  evaluation and send notification to the staff or not; this option does not
  prevent error handlers from execution

``submission_id``
  the ID of the evaluated :class:`~oioioi.contest.model.Submission` instance.

``program_source``
  :term:`Filetracker` path to a program source code.

``program_binary``
  :term:`Filetracker` path to an executable built from the ``program_source``.

``compiler_output``
  compiler stderr and stdout

``compilation_result``
  ``'SUCCESS'`` or ``'FAILURE'``

``tests``
  a dict which maps test names to their descriptions (dicts), like this::

    {
        '1a': {
            name: '1a',
            group: '1',
            kind: 'EXAMPLE',
            max_score: 5,
            exec_time_limit: 5000,
            exec_mem_limit: 65536,
            in_file: 'path',   # a filetracker file path
            hint_file: 'path2', # as above; contains model output
        },
    }

  The inner dictionaries are passed directly to :term:`workers`' program
  execution job.

``output_checker``
  :term:`Filetracker` path of an executable, which can check output.
  `None` means that submission output should be simply compared with
  the output file.

``test_scoring_function``
  :term:`Dotted name` of a function which will be used to grade tests results.

``test_results``
  a dict of dicts in form of::

    {
        'test_name': dict_returned_by_a_worker # see sio-exec documentation
    }

  Test grading adds another key in the test dict `score`

``group_results``
  a dict of dicts like this::

    {
        'group_name': {
            'status': 'OK'
            'score': <serialized ScoreValue, for example 'int:10'>,
        }
    }

``status``
  final submission status ('CE', 'WA', 'OK', etc.)

``score``
  final submission score (serialized
  :class:`~oioioi.contest.scores.ScoreValue`, for example ``'int:100'``)

Example
^^^^^^^

TODO

`Handlers`
----------

.. rem automodule:: oioioi.programs.handlers
   :members:

