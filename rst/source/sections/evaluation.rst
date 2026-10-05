=====================
Submission evaluation
=====================

Submission evaluation is definitely a long task that can't be handled in a
single HTTP request. Thus there is a need for an asynchronous judging system.

Evaluation system was designed with reliability in mind. In rare cases a task
may be evaluated twice, but can never be lost. When ownership of a task is
transferred between components, a sender deletes its own copy only after a
receiver signals that the task is successfully stored.


Components overview
-------------------

Information about evaluated tasks is carried in dictionaries called
`environment` which also define how the task should be evaluated (control is
defined by a list of instructions called `recipe`). Various available
fields and their meaning will be explained in depth later in this
document.

The evaluation system consists of two main parts, `evalmgr` that manages
state of asynchronous tasks and `sioworkersd` that handles groups of `workers`
and executes tasks on them. In detail, many separeate components take part in
the evaluation process:

- `oioioi`

  A web interface. In evaluation process it's responsible for as little as
  possible to minimize amount of work done in single HTTP request. It only
  creates an `environment` and places it in the tasks queue for `evalmgr`.

- `tasks queue`

  A celery_ broker_ that acts as a buffer between components sending tasks
  to `evalmgr` and `evalmgr` itself. It must receive and store tasks quickly
  (so that handing tasks to `evalmgr` never blocks).

  The default choice in `oioioi` is a `rabbitmq`_ broker.

  For details about how to insert a task into the queue see
  :meth:`~oioioi.evalmgr.delay_environ`.

- `evalmgr`

  An evaluation manager built on top of the celery_ system. It takes a task
  from `tasks queue` and processes it in loop as long as possible (until the
  end of a recipe, or a job transfer). Tasks performed by evalmgr aren't cpu
  consuming or blocking (such things are performed from `sioworkersd`), so
  `evalmgr` can be a single process on the same machine as `oioioi`. Instead
  it performs management steps like:

  - preparing `environment` before test (initial and final ones)
  - saving test results in database and informing the user via notification
    manager
  - monitoring jobs' state and stopping cancelled jobs (when `evalmgr`
    receives a job that has been cancelled, it ignores it).

  In eval system `evalmgr` is the only place where `oioioi`'s database
  can be changed (due to django_celery_ magic it's possible to use Django's
  models in `evalmgr`).

  `Evalmgr` provides a web interface for tracking (and managing) current jobs,
  available at ``admin/evalmgr/queuedjob/``. Possible states are `Queued` (for
  jobs waiting in `tasks queue`), `In progress` (for jobs currently processed
  by `evalmgr`), `Cancelled` (for jobs that have been canceled, but haven't
  been removed from system yet) and `Waiting` (for jobs sent from `evalmgr` to
  an external evaluation system like `sioworkersd`). There is a limited
  possibility of cancelling jobs that are outside of `evalmgr`, they aren't
  removed from system immediately, but are dropped as sooon as `evalmgr`
  starts to process them.

- `sioworkersd`

  A `workers` manager, keeps track of connected `workers` and runs selected
  tasks on them. When the whole task is finished, it's returned to `evalmgr`
  via `receive_from_workers`.

  For details on how to communicate with it from handlers in `evalmgr` see
  :py:meth:`~oioioi.evalmgr.transfer_job` and :py:mod:`~oioioi.sioworkers`.

  Its code is not a part of the OIOIOI Django project, instead it lives
  in ``sioworkers`` subfolder in the Git tree. For more information have
  a look at an overview in the `Sioworkersd documentation`_.

.. _Sioworkersd documentation: ../../../../sioworkers/rst/build/html/index.html

- `workers`

  Machines on which cpu intensive tasks (compilation, safe execution etc.) are
  executed, they connect to `sioworkersd` and perform single, indivisible
  tasks. For details see documentation on `sioworkersd`.

- `receive_from_workers`

  A HTTP daemon that acts as a pipe between `sioworkersd` and `evalmgr`. It
  receives an `environment` via HTTP and sends it to `evalmgr`.

- `filetracker`

  A HTTP-based file storage used as a database accessible by every component of
  the system. Huge files (like tests or sandboxes) aren't added to
  `environment`, but exposed as objects in `filetracker` database and
  accessible via HTTP with filepath-like keys. Filetracker has a cache and
  cache cleaning mechanisms and thus reduces brandwidth and storage usage (as
  frequently used files are available locally, there is no need for
  downloading them).

  It's a separate project and lives in `filetracker github project`_.

.. _celery: http://www.pythondoc.com/celery-3.1.11/
.. _broker: http://www.pythondoc.com/celery-3.1.11/getting-started/brokers/
.. _rabbitmq: http://www.rabbitmq.com/
.. _`filetracker github project`: https://github.com/sio2project/filetracker


Evaluation environment
----------------------

An `environment` is a dict which contains all data necessary to complete
a `job` and describes how to do it. `environment['recipe']` contains a list
of functions (`handlers`) which need to be called to do the work.

A `handler` is a function like this::

  def handler(environment, **kwargs):
      # ... do something ...
      return modified_environment

The `handler` simply gets the `environment`
(and optionally -- additional args specified in `environment['recipe']`
) and returns a modified `environment`, which is then passed to the next
handler, and so on.

Therefore each `handler` does some work (e.g. runs tests, judges tests,
compiles a program...) based on the `environment` state and saves the results
into it. For implementation details and various helpers consult
:py:mod:`~oioioi.evalmgr` module.

Environment for submission evaluation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The evaluation environment is created when a new submission arrives or a
rejudge request is received. The basic environment is created by
:meth:`~oioioi.evalmgr.create_environ` and filled by
:meth:`~oioioi.contests.controllers.ContestController.fill_evaluation_environ`.

.. automethod:: oioioi.contests.controllers.ContestController.fill_evaluation_environ
    :noindex:

.. automethod:: oioioi.evalmgr.create_environ
    :noindex:


What's in the environment?
^^^^^^^^^^^^^^^^^^^^^^^^^^

``recipe``
  a list of tuples in form of ``[ (handler_name, handler_path, [kwargs]),
  ...]``, where:

  * ``handler_name`` is a unique identifier of the  `Handler` in the
    ``recipe``,

  * ``handler_path`` is a :term:`dotted name` of the `Handler` function,

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

Simple environment generated when submission is being judged::

    {
        # Job identifier in celery system
        'job_id': 'urn:uuid:2e9dd7f1-d58f-49bc-a2e3-a56dbab8047d',

        # Name of web instance that created this environment
        'oioioi_instance': 'OIOIOI',

        # Basic informations about the submission itself
        'submission_id': 95,
        'submission_owner': 'username',
        'submission_kind': 'NORMAL',
        'source_file': '/submissions/pa/95.c@1497277351',   # A filetracker key
        'language': 'c',
        'is_rejudge': False,

        # Options related to contest
        'contest_id': 'some_contest_id',
        'round_id': 3,

        # Options for the compilation step
        'compilation_result_size_limit': 10485760,
        'extra_compilation_args': ['-DELOZIOM'],
        'extra_files': {
            'makra.h': '/problems/3/makra.h@1494964934'},

        # Informations related to a programming problem
        'problem_id': 3,
        'problem_instance_id': 6,
        'problem_short_name': u'sum',

        # Options that determines how the tests are run
        'exec_mode': 'cpu',

        # And how results are checked and scored
        'checker': '/problems/3/d0051f2a-...',
        'untrusted_checker': True,

        # Priorieties assigned to this submission
        'contest_weight': 1000,
        'contest_priority': 10,

        # Those determines how results from tests are translated into the
        # points, and how they will be presented to user.
        'group_scorer': 'oioioi.programs.utils.min_group_scorer',
        'score_aggregator': 'oioioi.programs.utils.sum_score_aggregator',
        'test_scorer': 'oioioi.pa.utils.pa_test_scorer',
        'report_kinds': ['INITIAL', 'NORMAL']

        # Miscellaneous other options
        'extra_args': {},

        # Recipe, numbers of steps relate to 'Way of typical submission'
        # section below.
        'recipe': [
            # Step 4, preparing submission for compilation
            ('wait_for_submission_in_db',
                'oioioi.contests.handlers.wait_for_submission_in_db'),
            ('check_problem_instance_state',
                'oioioi.suspendjudge.handlers.check_problem_instance_state',
                {'suspend_init_tests': True}),

            # Steps 5-7, actual compilation ('compile' handler sends
            # environment to sioworkersd) and checking its results
            ('compile',
                'oioioi.programs.handlers.compile'),
            ('compile_end',
                'oioioi.programs.handlers.compile_end'),
            ('after_compile',
                'oioioi.evalmgr._placeholder'),

            # Steps 7-12, preparation before initial tests,
            # and running them
            ('collect_tests',
                'oioioi.programs.handlers.collect_tests'),
            ('initial_run_tests',
                'oioioi.programs.handlers.run_tests',
                {'kind': 'EXAMPLE'}),
            ('initial_run_tests_end',
                'oioioi.programs.handlers.run_tests_end'),

            # Beginning of step 13, saving initial tests' results
            ('initial_grade_tests',
                'oioioi.programs.handlers.grade_tests'),
            ('initial_grade_groups',
                'oioioi.programs.handlers.grade_groups'),
            ('initial_grade_submission',
                'oioioi.programs.handlers.grade_submission',
                {'kind': 'EXAMPLE'}),

            # And publishing them to user
            ('initial_make_report',
                'oioioi.programs.handlers.make_report',
                {'kind': 'INITIAL'}),
            ('update_report_statuses',
                'oioioi.contests.handlers.update_report_statuses'),
            ('update_submission_score',
                'oioioi.contests.handlers.update_submission_score'),
            ('update_report_statuses',
                'oioioi.contests.handlers.update_report_statuses'),
            ('update_submission_score',
                'oioioi.contests.handlers.update_submission_score'),
            ('after_initial_tests',
                'oioioi.evalmgr._placeholder'),

            ('check_problem_instance_state',
                'oioioi.suspendjudge.handlers.check_problem_instance_state'),

            # Steps 13-17, preparation before final tests,
            # and running them
            ('before_final_tests',
                'oioioi.evalmgr._placeholder'),
            ('final_run_tests',
                'oioioi.programs.handlers.run_tests',
                {'kind': 'NORMAL'}),
            ('final_run_tests_end',
                'oioioi.programs.handlers.run_tests_end'),

            # Step 18, processing final tests' results
            ('final_grade_tests',
                'oioioi.programs.handlers.grade_tests'),
            ('final_grade_groups',
                'oioioi.programs.handlers.grade_groups'),
            ('final_grade_submission',
                'oioioi.programs.handlers.grade_submission'),
            ('final_make_report',
                'oioioi.programs.handlers.make_report'),
            ('after_final_tests',
                'oioioi.evalmgr._placeholder'),

            # Cleaning
            ('delete_executable',
                'oioioi.programs.handlers.delete_executable'),

            # And publishing final results to the user
            ('update_report_statuses',
                'oioioi.contests.handlers.update_report_statuses'),
            ('update_submission_score',
                'oioioi.contests.handlers.update_submission_score'),
            ('update_user_results',
                'oioioi.contests.handlers.update_user_results'),
            ('call_submission_judged',
                'oioioi.contests.handlers.call_submission_judged'),

            # Some debugging step
            ('dump_final_env',
                'oioioi.evalmgr.handlers.dump_env',
                {'message': 'Finished evaluation'})],

        # This handlers are run, when an error occurs during evaluation,
        # due to a bug in oioioi code.
        'error_handlers': [
            ('remove_queuedjob_on_error',
                'oioioi.evalmgr.handlers.remove_queuedjob_on_error'),
            ('delete_executable',
                'oioioi.programs.handlers.delete_executable'),
            ('create_error_report',
                'oioioi.contests.handlers.create_error_report'),
            ('mail_admins_on_error',
                'oioioi.contests.handlers.mail_admins_on_error'),
            ('update_report_statuses',
                'oioioi.contests.handlers.update_report_statuses'),
            ('update_submission_score',
                'oioioi.contests.handlers.update_submission_score'),
            ('update_user_results',
                'oioioi.contests.handlers.update_user_results'),
            ('call_submission_judged',
                'oioioi.contests.handlers.call_submission_judged'),
            ('dump_final_env',
                'oioioi.evalmgr.handlers.dump_env',
                {'message': 'Finished evaluation'}),
            ('error_handled',
                'oioioi.evalmgr.handlers.error_handled')]
    }


How the recipe is being processed
---------------------------------

To initialize processing of an `environment` it must be inserted into
`tasks queue` with :meth:`~oioioi.delay_environ`. Later, when `evalmgr` takes
an `environment` from the queue, handlers are executed from the beginning,
one after the other in :meth:`~oioioi.evalmgr.evalmgr_job`.

.. automethod:: oioioi.evalmgr.delay_environ
.. automethod:: oioioi.evalmgr.evalmgr_job

How is the environment send to sioworkersd
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It's done using evalmgr mechanism for sending jobs to an external evaluation
system. Handler which wants to send environment should look like::

  def transfer_handler(environment):
      # ... do some important stuff ...
      return transfer_job(environment, 'transfer_function name')

For `sioworkersd` transfer function is defined as
:meth:`~oioioi.sioworkers.handlers.transfer_job`.

.. automethod:: oioioi.evalmgr.transfer_job

Way of a typical submission
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Scheme that a typical submission follows (components responsible for environment
during each step are written in **bold**) is:

1. **oioioi**, `filetracker`

   A user submits a solution, a new evaluation environment is created.

2. `oioioi`, **tasks queue**

   Fresh `environment` gets to the `tasks queue`, where it waits for being
   processed.

3. `tasks queue`, **evalmgr**

   `Evalmgr` takes `environment` from the `tasks queue` and processes handlers
   from its `recipe` in a loop. It prepares the submission for compilation.

4. `evalmgr`, **sioworkersd**

   `Evalmgr` transfers `environment` to `sioworkersd`.

5. **sioworkersd**, `workers`, `filetracker`

   `Sioworkersd` creates a compilation task from the `environment` and runs
   it on some free `worker`. The resulting binary is inserted into
   `filetracker` database and `environment` is updated with compilation results.

6. `sioworkersd`, `receive_from_workers`, **tasks queue**

   `Environment` is sent back to `receive_from_workers` which immediately
   inserts it into the `tasks queue`.

7. `tasks queue`, **evalmgr**

   `Evalmgr` takes `environment` from the `tasks queue` and checks
   compilation results. If they are successful the evaluation continues,
   otherwise it's stopped now, and the information about the compilation error
   is inserted into the database (so that user can see it in `oioioi`). Also
   a notification can be emitted.

8. **evalmgr**

   `Evalmgr` continues processing `environment`, now preparing it for running
   the initial tests.

9. `evalmgr`, **sioworkersd**

   Prepared `environment` is transferred to `sioworkersd`.

10. **sioworkersd**

    `Sioworkersd` creates many separate tasks from the `environment`, one for
    each initial test.

11. **sioworkersd**, `workers`, `filetracker`

    Created tasks are queued and sent to `workers`. `Sioworkersd` gathers
    results from the tasks, waiting for all of them to finish.

12. `sioworkersd`, `receive_from_workers`, **tasks queue**

    When every task created for the `environment` has finished, the evaluation
    report is inserted into the `environment` which is then sent
    back to `receive_from_workers` and inserted into the `tasks queue`.

13. `tasks queue`, **evalmgr**

    `Evalmgr` takes `environment` from the `tasks queue` again. It saves
    initial tests results in the database and optionally emits a notification
    to the user. Then it prepares the `environment` for running final tests.

14-17. `evalmgr`, **sioworkersd**, `receive_from_workers`, **tasks queue**

    `Evaluation` continues in exactly same way as for initial tests (points
    9-12).

18. `tasks queue`, **evalmgr**

    `Evalmgr` takes `environment` from the `tasks queue` once again. Results
    from final tests are saved into the database and optionally a notification
    is emitted. The submission has been successfully judged.
