import logging

import sys

from django.conf import settings
from django.contrib import messages
from django.core.files import File
from django.core.urlresolvers import reverse
from django.db import transaction
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.encoding import smart_str
from django.utils.http import urlencode
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils import uploaded_file_name
from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.utils import is_contest_basicadmin
from oioioi.problems.forms import PackageUploadForm, ProblemsetSourceForm
from oioioi.problems.models import Problem, ProblemPackage
from oioioi.problems.package import backend_for_package
from oioioi.problems.unpackmgr import unpackmgr_job
from oioioi.problems.utils import (get_new_problem_instance,
                                   update_tests_from_main_pi,
                                   can_upload_problems)

logger = logging.getLogger(__name__)


def problem_sources(request, existing_problem=False):
    sources = []
    for name in settings.PROBLEM_SOURCES:
        obj = import_string(name)()
        if isinstance(obj, ProblemSource):
            sources.append(obj)
        else:
            for item in obj:
                sources.append(item)
    sources = [s for s in sources if s.is_available(request)]

    def is_source(source):
        return not existing_problem or isinstance(source, UploadedPackageSource)

    return list(filter(is_source, sources))


class ProblemSource(object):
    #: A simple identifier, which may appear in the URL.
    key = '__override_in_a_subclass__'

    #: A human-readable description, which will be displayed in a tab.
    short_description = '__override_in_a_subclass__'

    def view(self, request, contest, existing_problem=None):
        """Renders the view where the user can upload the file or
           point out where to get the problem from.

           If the request method is ``GET``, it should return rendered HTML,
           which will be injected in an appropriate div element.
           :class:`~django.template.response.TemplateResponse` is fine, too.

           If the request method is ``POST``, it should start the
           unpacking proccess. If no errors occur, it should return
           :class:`~django.http.HttpResponseRedirect`
           (e.g. to a view with problem packages queued for processing).

           :param request: Django request
           :param contest: :class:`~oioioi.contests.models.Contest` where the
            problem is going to be attached (or is already attached); may be
            ``None``.
           :param existing_problem: :class:`~oioioi.problems.models.Problem`
            to update (if problem update was requested)
        """
        raise NotImplementedError

    def is_available(self, request):
        """Returns ``True`` if the source is available for the given
           request."""
        return True


class PackageSource(ProblemSource):
    key = 'upload'
    short_description = _("Upload package")

    #: Template to use for rendering the form.
    template_name = 'problems/package-source.html'

    def make_form(self, request, contest, existing_problem=None):
        """Creates a form, which can be later filled in by the user with
           information necessary for obtaining the problem package.

           If the request method is ``POST``, then the form should be filled
           with its data.
        """
        raise NotImplementedError

    def get_package_file(self, request, contest, form, existing_problem=None):
        """Extracts the information from the validated form and returns the
           package file provided by the user.

           Should return a pair ``(filename, file_manager)``, where
           ``filename`` is the original name of the file specified by the user
           and ``file_manager`` is a context manager.
           This ``file_manager`` will be later used like this:

            .. python::

                with file_manager as path:
                    process the file pointed to by ``path``

            Moreover, ``file_manager`` should take care of unlinking the file
            if this is necessary.

            The ``filename`` may be ``None`` if the name of the file returned
            by the ``file_manager`` ends with an appropriate extension
            (so that it is possible to choose the right backend for it).
        """
        raise NotImplementedError

    def choose_backend(self, path, original_filename=None):
        """Returns the dotted name of a
           :class:`~oioioi.package.ProblemPackageBackend` suitable for
           processing a given package.

           This function is called when an unpacking environment is created,
           i.e. from
           :meth:`~oioioi.problems.problem_sources.ProblemSource.create_env`.
        """
        return backend_for_package(path, original_filename)

    def create_package_instance(self, request, contest, path,
            existing_problem=None, original_filename=None):
        """Creates a :class:`~oioioi.problems.models.ProblemPackage` instance
           from a given package file.
        """
        package = ProblemPackage.objects.create(contest=contest,
                created_by=request.user)
        package_name = original_filename or path
        package.package_file.save(package_name, File(open(path, 'rb')))
        if existing_problem:
            package.problem = existing_problem
        package.save()
        return package

    def create_env(self, request, contest, form, path, package,
            existing_problem=None, original_filename=None):
        """Creates an environment which will be later passed to
           :func:`~oioioi.problems.unpackmgr.unpackmgr_job`.
        """
        backend_name = self.choose_backend(path, original_filename)
        backend = import_string(backend_name)()
        if package.problem:
            package.problem_name = package.problem.short_name
        else:
            package.problem_name = backend.get_short_name(path,
                    original_filename)
        package.save()
        env = {}
        env['post_upload_handlers'] = \
                ['oioioi.problems.handlers.update_problem_instance']
        env['backend_name'] = backend_name
        env['package_id'] = package.id
        env['round_id'] = form.cleaned_data.get('round_id', None)
        if contest:
            env['contest_id'] = contest.id
        env['author'] = request.user.username
        if existing_problem:
            env['is_reupload'] = True
        else:
            env['is_reupload'] = False
        env['visibility'] = form.cleaned_data.get('visibility', Problem.VISIBILITY_FRIENDS)

        return env

    def _redirect_response(self, request):
        return redirect('oioioiadmin:problems_%sproblempackage_changelist' %
                ('' if request.user.is_superuser else 'contest'))

    def handle_form(self, form, request, contest, existing_problem=None):
        if form.is_valid():
            try:
                # We need to make sure that the package is saved in the
                # database before the Celery task starts.
                with transaction.atomic():
                    original_filename, file_manager = \
                        self.get_package_file(request, contest, form,
                                              existing_problem)
                    with file_manager as path:
                        package = self.create_package_instance(request,
                                                               contest, path, existing_problem,
                                                               original_filename)
                        env = self.create_env(request, contest, form, path,
                                              package, existing_problem,
                                              original_filename)
                        if contest:
                            contest.controller.fill_upload_environ(request,
                                                                   form, env)
                        package.save()
                    async_task = unpackmgr_job.s(env)
                    async_result = async_task.freeze()
                    ProblemPackage.objects.filter(id=package.id).update(
                        celery_task_id=async_result.task_id)
                async_task.delay()
                return True

            # pylint: disable=broad-except
            except Exception as e:
                logger.error("Error processing package", exc_info=True,
                             extra={'omit_sentry': True})
                form._errors['__all__'] = form.error_class([smart_str(e)])

        return False

    def view(self, request, contest, existing_problem=None):
        form = self.make_form(request, contest, existing_problem)
        if contest:
            contest.controller.adjust_upload_form(request, existing_problem,
                                                  form)
        if request.method == 'POST':
            if self.handle_form(form, request, contest, existing_problem):
                if request.user.is_superuser or \
                        (request.contest and is_contest_basicadmin(request)):
                    messages.success(request,
                                     _("Package queued for processing."))
                    return self._redirect_response(request)
                messages.success(request,
                                 _("Package queued for processing. It will appear in "
                                   "problem list when ready. Please be patient."))
        return TemplateResponse(request, self.template_name, {'form': form})


class UploadedPackageSource(PackageSource):
    def make_form(self, request, contest, existing_problem=None):
        if request.method == 'POST':
            return PackageUploadForm(contest, existing_problem, request.POST, request.FILES,
                                     user=request.user)
        else:
            return PackageUploadForm(contest, existing_problem, user=request.user)

    def get_package_file(self, request, contest, form, existing_problem=None):
        package_file = request.FILES['package_file']
        return package_file.name, uploaded_file_name(package_file)

    def is_available(self, request):
        # Removes the "Upload Package" form if the user
        # doesn't have the permission to use it.
        return can_upload_problems(request)


class ProblemsetSource(ProblemSource):
    key = 'problemset_source'
    short_description = _('Add from Problemset')

    def view(self, request, contest, existing_problem=None):
        if not contest:
            messages.warning(request, _("Option not available"))
            path = request.path
            if existing_problem:
                path += '?' + urlencode({'problem': existing_problem.id})
            return safe_redirect(request, path)

        is_reupload = existing_problem is not None
        if existing_problem:
            url_key = existing_problem.problemsite.url_key
        else:
            # take url_key form form
            url_key = request.POST.get('url_key', None)
        if url_key is None:
            # take url_key from Problemset
            url_key = request.GET.get('url_key', None)

        form = ProblemsetSourceForm(url_key)
        post_data = {'form': form, 'is_reupload': is_reupload}

        if request.POST:
            if not Problem.objects.filter(problemsite__url_key=url_key) \
                    .exists():
                messages.warning(request, _('Given url key is invalid'))
                return TemplateResponse(request,
                        "problems/problemset-source.html",
                        post_data)

            problem = Problem.objects.get(problemsite__url_key=url_key)
            if existing_problem:
                assert problem == existing_problem
                assert 'instance_id' in request.GET
                pi = problem.probleminstance_set.get(contest=contest,
                                            id=request.GET['instance_id'])
                update_tests_from_main_pi(pi)
                # limits could be changed
                pi.needs_rejudge = True
                pi.save()
                messages.success(request, _("Problem successfully updated"))
            else:
                pi = get_new_problem_instance(problem, contest)
                messages.success(request, _("Problem successfully uploaded"))
            return safe_redirect(request, reverse(
                    'oioioiadmin:contests_probleminstance_changelist'))

        return TemplateResponse(request, "problems/problemset-source.html",
                                post_data)
