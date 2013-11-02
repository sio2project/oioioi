# pylint: disable=W0703
# Catching too general exception Exception
from django.conf import settings
from django import forms
from django.db import transaction
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from oioioi.base.utils import uploaded_file_name, get_object_by_dotted_name, \
        memoized
from oioioi.problems.package import backend_for_package
import logging

logger = logging.getLogger(__name__)


@memoized
def problem_sources(request):
    sources = []
    for name in settings.PROBLEM_SOURCES:
        obj = get_object_by_dotted_name(name)()
        if isinstance(obj, ProblemSource):
            sources.append(obj)
        else:
            for item in obj:
                sources.append(item)
    sources = [s for s in sources if s.is_available(request)]
    return sources


class ProblemSource(object):
    #: A simple identifier, which may appear in the URL.
    key = '__override_in_a_subclass__'

    #: A human-readable description, which will be displayed in a tab.
    short_description = '__override_in_a_subclass__'

    def view(self, request, round, existing_problem=None):
        """Renders the view where the user can upload the file or
           point out where to get the problem from.

           If should return rendered HTML, which will be injected in
           an appropriate div element.
           :class:`~django.template.response.TemplateResponse` is fine, too.

           May return an instance of :class:`~oioioi.problems.models.Problem`
           which indicates that the operation has been finished and the user
           should be redirected back to the list of problems (or asked to
           attach the new problem to some round).

           :param request: Django request
           :param round: :class:`~oioioi.contests.models.Round` where the
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


class PackageUploadForm(forms.Form):
    package_file = forms.FileField(label=_("Package file"))


class PackageSource(ProblemSource):
    key = 'upload'
    short_description = _("Upload package")

    #: Template to use for rendering the form.
    template_name = 'problems/package_source.html'

    def process_package(self, request, contest, filename,
            original_filename, existing_problem=None):
        backend = backend_for_package(filename,
                original_filename=original_filename)
        problem = backend.unpack(filename,
                original_filename=original_filename,
                existing_problem=existing_problem)
        messages.success(request, _("Problem package uploaded."))
        return problem

    def process_valid_form(self, request, contest, form,
            existing_problem=None):
        uploaded_file = request.FILES['package_file']
        with uploaded_file_name(uploaded_file) as filename:
            return self.process_package(request, contest, filename,
                    uploaded_file.name, existing_problem)

    def make_form(self, request, contest, existing_problem=None):
        if request.method == 'POST':
            return PackageUploadForm(request.POST, request.FILES)
        else:
            return PackageUploadForm()

    def view(self, request, contest, existing_problem=None):
        form = self.make_form(request, contest, existing_problem)
        if request.method == 'POST':
            if form.is_valid():
                try:
                    with transaction.commit_on_success():
                        return self.process_valid_form(request, contest, form,
                            existing_problem)
                except Exception, e:
                    logger.error("Error processing package", exc_info=True)
                    form._errors['__all__'] = form.error_class([unicode(e)])
        return TemplateResponse(request, self.template_name,
                {'form': form})
