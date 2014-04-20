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
environment.

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
