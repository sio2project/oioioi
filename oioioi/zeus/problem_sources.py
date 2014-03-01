from django.conf import settings
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils import uploaded_file_name
from oioioi.problems.models import Problem
from oioioi.problems.problem_sources import PackageSource
from oioioi.zeus.forms import ZeusProblemForm
from oioioi.zeus.models import ZeusProblemData
from oioioi.zeus.package import ZeusPackageBackend


class ZeusProblemSource(PackageSource):
    key = 'zeus'
    short_description = _("Add Zeus problem")

    def __init__(self, zeus_instances=None):
        if zeus_instances is None:
            zeus_instances = [(zeus_id, '%s: %s' % (zeus_id, url))
                              for zeus_id, (url, _login, _secret)
                              in settings.ZEUS_INSTANCES.iteritems()]
        self.zeus_instances = zeus_instances

    def process_package(self, request, contest, filename,
                        original_filename, existing_problem=None):
        backend = ZeusPackageBackend(filename,
                                     original_filename=original_filename)
        problem = backend.unpack(filename,
                                 original_filename=original_filename,
                                 existing_problem=existing_problem)
        return problem

    def process_valid_form(self, request, contest, form,
                           existing_problem=None):
        uploaded_file = request.FILES['package_file']
        with uploaded_file_name(uploaded_file) as filename:
            problem = self.process_package(request, contest, filename,
                    uploaded_file.name, existing_problem)
            if isinstance(problem, Problem):
                problem_data, _created = ZeusProblemData.objects \
                    .get_or_create(problem=problem)
                problem_data.zeus_id = form.cleaned_data['zeus_id']
                problem_data.zeus_problem_id = \
                    form.cleaned_data['zeus_problem_id']
                problem_data.save()
            messages.success(request, _("ZeusProblem package uploaded."))
            return problem

    def make_form(self, request, contest, existing_problem=None):
        initial = {}
        if existing_problem:
            try:
                zp = ZeusProblemData.objects.get(problem=existing_problem)
                initial = {
                    'zeus_id': zp.zeus_id,
                    'zeus_problem_id': zp.zeus_problem_id,
                }
            except ZeusProblemData.DoesNotExist:
                pass

        if request.method == 'POST':
            return ZeusProblemForm(self.zeus_instances, contest, request.POST,
                                   request.FILES, initial=initial)
        else:
            return ZeusProblemForm(self.zeus_instances, contest,
                                   initial=initial)
