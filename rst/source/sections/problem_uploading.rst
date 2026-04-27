=================
Problem uploading
=================

Problem sources
---------------

Let us consider the most typical use case.
A contest admin decides to upload a new problem or modify an existing one.
Depending on the OIOIOI installation there could be many sources of the
problem. Such a source should inherit from the
:class:`~oioioi.problems.problem_sources.ProblemSource`.

.. autoclass:: oioioi.problems.problem_sources.ProblemSource

    .. automethod:: oioioi.problems.problem_sources.ProblemSource.view

    .. automethod:: oioioi.problems.problem_sources.ProblemSource.is_available

The complete list of available ``problem sources`` can be specified in the
``deployment/settings.py`` file under the ``PROBLEM_SOURCES`` name. The listed
``problem sources`` will be displayed as tabs of the problem upload view,
provided that their
:meth:`~oioioi.problems.problem_sources.ProblemSource.is_available` method
returns ``True``.


Developers are expected to implement their custom ``problem sources`` by
inheriting from the above-mentioned class, such code should be preferably
placed in a ``problem_sources`` module in a given app.

Package sources
---------------

The most basic problem source is a
:class:`~oioioi.problems.problem_sources.PackageSource`. It may be used when
all the data necessary for creating a problem may be uploaded in a single file.

.. autoclass:: oioioi.problems.problem_sources.PackageSource

    .. automethod:: oioioi.problems.problem_sources.PackageSource.make_form

    .. automethod:: oioioi.problems.problem_sources.PackageSource.get_package

    .. automethod:: oioioi.problems.problem_sources.PackageSource.create_package_instance

    .. automethod:: oioioi.problems.problem_sources.PackageSource.choose_backend

    .. automethod:: oioioi.problems.problem_sources.PackageSource.create_env

Since every instance of :class:`~oioioi.problems.problem_sources.PackageSource`
is associated with a file of some kind, the file, together with some additional
data, is represented as a separate model, namely the
:class:`~oioioi.problems.models.ProblemPackage`. Such a design is quite natural
when combined with the ``unpacking manager`` pipeline, which is described
below.

Unpacking manager
-----------------

.. _Celery: http://docs.celeryproject.org/en/latest/index.html

When a user uploads a problem via the
:class:`~oioioi.problems.problem_sources.PackageSource`, an unpacking
environment is created and passed to a new `Celery`_ task, that
is to :func:`~oioioi.problems.unpackmgr.unpackmgr_job`.

.. autofunction:: oioioi.problems.unpackmgr.unpackmgr_job(env)

The above-mentioned ``post-upload handlers`` are functions, which accept an
environment (a dictionary) as their only argument and return the modified
environment. Before the handlers are called,
the following new ``env`` keys are produced:
``job_id``: the ``Celery`` task id
`problem_id``: id of the
:class:`~oioioi.problems.models.ProblemPackage`
instance, which was created or modified

Normally, when you add a new :class:`~oioioi.problems.models.Problem`,
you want to attach it to a specific :class:`~oioioi.contests.models.Round`
of a given :class:`~oioioi.contests.models.Contest`. That is why the default
implementation of :class:`~oioioi.problems.problem_sources.PackageSource`
specifies one ``post-upload handler``, namely
:func:`~oioioi.problems.handlers.create_problem_instance`.

.. autofunction:: oioioi.problems.handlers.create_problem_instance(env)

Problem package backends
------------------------

The :class:`~oioioi.problems.problem_sources.PackageSource` class
defines how problem data should be uploaded by
a user, which keys should be present in the unpacking environment and
what should be done after the new :class:`~oioioi.problems.models.Problem`
is created. However, it is not involved in the actual unpacking and processing
of the uploaded file.
It only chooses an appropriate
:class:`~oioioi.problems.package.ProblemPackageBackend`
(:meth:`~oioioi.problems.problem_sources.PackageSource.choose_backend`) and
delegates this responsibility to it.

oioioi.problems.package
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: oioioi.problems.package
   :members:

oioioi.sinolpack.package
^^^^^^^^^^^^^^^^^^^^^^^^

Provides :class:`~oioioi.problems.package.ProblemPackageBackend`
implementation to deal with
Sinol packages - standardized archives with problem data.
Sinolpack is OIOIOI standard problem package format.
The detailed archive content description can be found here:
https://sio2project.mimuw.edu.pl/display/DOC/Preparing+Task+Packages.

.. automodule:: oioioi.sinolpack.package
   :members:

config.yml reference
""""""""""""""""""""

Sinol packages may include a ``config.yml`` file in the package root to
configure problem settings. Below are the supported keys:

``title``
    The problem's full name/title.

``title_xx`` (where ``xx`` is a language code, e.g. ``title_en``, ``title_pl``)
    Language-specific problem title.

``sinol_task_id``
    Task identifier used for validation against the package short name.

``time_limit``
    Global time limit in milliseconds (default: 10000).

``time_limits``
    Dictionary mapping test group names to per-group time limits in
    milliseconds. Example::

        time_limits:
          1: 5000
          2: 10000

``memory_limit``
    Global memory limit in KiB (default: 66000).

``memory_limits``
    Dictionary mapping test group names to per-group memory limits in KiB.

``scores``
    Dictionary mapping test group names to their maximum scores. Example::

        scores:
          1: 20
          2: 30
          3: 50

``subtask_dependencies``
    Dictionary defining dependencies between test groups (subtasks). When a
    group depends on prerequisites, its score is calculated as if it also
    contained the prerequisite groups' tests (with scores normalized to the
    dependent group's scale). The score can only be lowered, never raised.
    A warning icon is shown in the report when a dependency lowers the score.

    Circular dependencies are not allowed and will be rejected during package
    upload. Example::

        subtask_dependencies:
          2: [1]
          3: [1, 2]

    In this example, group 2 depends on group 1, and group 3 depends on
    both groups 1 and 2.

``override_limits``
    Dictionary mapping programming languages to per-language time/memory limit
    overrides. Example::

        override_limits:
          py:
            time_limit: 20000
            memory_limit: 132000

``library``
    Name of a library file needed during compilation.

``extra_compilation_files``
    List of extra files needed during compilation.

``extra_execution_files``
    Dictionary mapping language codes to lists of files needed during
    execution.

``no_outgen``
    Boolean flag to disable automatic test output generation.
