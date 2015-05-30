""" This module contains a problem package backend interface. You should
    create a ``package.py`` file in your new app and implement your package
    backend (inheriting from
    :class:`~oioioi.problems.package.ProblemPackageBackend`)
    whenever you introduce a new problem package format.
"""

import logging
from django.conf import settings
from django.core.files import File
from oioioi.base.utils import RegisteredSubclassesBase, ObjectWithMixins, \
        get_object_by_dotted_name
from oioioi.problems.models import ProblemPackage, Problem

logger = logging.getLogger(__name__)


class ProblemPackageError(StandardError):
    """A generic exception to be used by or subclassed by backends."""
    pass


class ProblemPackageBackend(RegisteredSubclassesBase, ObjectWithMixins):
    """A class which manages problem packages.

       The main functionality is extracting archives with problem statements,
       data, model solutions etc. and building
       :class:`~oioioi.problems.models.Problem` instances.
    """

    description = '__human_readable_name_here__'
    abstract = True
    modules_with_subclasses = 'package'

    def identify(self, path, original_filename=None):
        """Checks if the backend is suitable for processing the specified
           problem package.

           :param path: a path to the processed problem package

           :param original_filename: the name of the package specified by the
           uploading user.

           Returns ``True`` if the backend can handle the specified problem
           package file.
        """
        raise NotImplementedError

    def get_short_name(self, path, original_filename=None):
        """Returns the problem's short name.

           :param path: a path to the processed problem package

           :param original_filename: the name of the package specified by the
           uploading user.
        """
        raise NotImplementedError

    def unpack(self, env):
        """Processes a package, creating a new
           :class:`~oioioi.problems.models.Problem` or updating an existing
           one.

           This function will be called either from
           :func:`~oioioi.problems.unpackmgr.unpackmgr_job` (Celery task)
           or from :func:`~oioioi.problems.package.simple_unpack` (e.g. when
           a problem is added from a command line).

           Used ``env`` keys:
             ``package_id``: an id of the
             :class:`~oioioi.problems.models.ProblemPackage` instance
             with the package file to unpack.

           Produced ``env`` keys:
             ``problem_id``: an id of the
             :class:`~oioioi.problems.models.Problem` instance
             representing the created or modified problem.
        """
        raise NotImplementedError

    def simple_unpack(self, filename, existing_problem=None):
        """This function may be used for unpacking outside unpackmgr.

           :param filename: a path to the problem package file

           :param existing_problem: an instance of
            :class:`~oioioi.problems.models.Problem` to be changed.
             If ``None``, a new :class:`~oioioi.problems.models.Problem` is
             created.

           Returns a :class:`~oioioi.problems.models.Problem` instance.
        """
        problem = None
        pp = ProblemPackage(problem=existing_problem)
        pp.package_file.save(filename, File(open(filename, 'rb')))
        env = {}
        if existing_problem:
            env['author'] = existing_problem.author
            pp.problem_name = existing_problem.short_name
        else:
            pp.problem_name = self.get_short_name(filename)
        pp.save()
        env['package_id'] = pp.id
        with pp.save_operation_status():
            self.unpack(env)
            problem = Problem.objects.get(id=env['problem_id'])
            pp.problem = problem
            pp.save()
        return problem

    def pack(self, problem):
        """Creates a package from problem, returns a
           :class:`django.http.HttpResponse` instance.

           Should raise ``NotImplementedError`` if creating packages is not
           supported.
        """
        raise NotImplementedError


class NoBackend(NotImplementedError):
    pass


def backend_for_package(filename, original_filename=None):
    """Finds a backend suitable for unpacking the given package and returns
       its dotted name.

       :param filename: a path to the processed problem package

       :param original_filename: the name of the package specified by the
       uploading user.
    """
    for backend_name in settings.PROBLEM_PACKAGE_BACKENDS:
        try:
            backend = get_object_by_dotted_name(backend_name)()
            if backend.identify(filename, original_filename):
                return backend_name
        # pylint: disable=broad-except
        except Exception:
            logger.warning('Backend %s probe failed', backend_name,
                    exc_info=True)
    raise NoBackend('Problem pack format not recognized')
