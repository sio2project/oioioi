from django.conf import settings
from oioioi.base.utils import RegisteredSubclassesBase, ObjectWithMixins, \
        get_object_by_dotted_name
import logging

logger = logging.getLogger(__name__)


class ProblemPackageError(StandardError):
    """A generic exception to be used by or subclassed by backends."""
    pass


class ProblemPackageBackend(RegisteredSubclassesBase, ObjectWithMixins):
    """A class which manages problem packages.

       The main functionality is extracting archives with problem statements,
       data, model solutions etc. and building
       :cls:`oioioi.problems.models.Problem` instances.
    """

    description = '__human_readable_name_here__'
    abstract = True
    modules_with_subclasses = 'package'

    def identify(self, path, original_filename=None):
        """Returns ``True`` if the backend can handle the specified problem
           package file."""
        raise NotImplementedError

    def unpack(self, path, original_filename=None, existing_problem=None):
        """Unpacks package, creating a new
           :cls:`oioioi.problems.models.Problem` or updating an existing one.

           Returns the created or updated ``Problem``.
        """
        raise NotImplementedError

    def pack(self, problem):
        """Creates a package from problem, returns a
           :class:`django.http.HttpResponse` instance.

           Should raise ``NotImplementedError`` if creating packages is not
           supported.
        """
        raise NotImplementedError


class NoBackend(Exception):
    pass


def backend_for_package(filename, original_filename=None):
    """Finds a backend suitable for unpacking the given package."""
    for backend_name in settings.PROBLEM_PACKAGE_BACKENDS:
        try:
            backend = get_object_by_dotted_name(backend_name)()
            if backend.identify(filename, original_filename):
                return backend
        except Exception:
            logger.warning('Backend %s probe failed', backend_name,
                    exc_info=True)
    else:
        raise NoBackend('Problem pack format not recognized')
