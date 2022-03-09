import six
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from oioioi.problems.models import Problem
from oioioi.problems.problem_sources import UploadedPackageSource
from oioioi.zeus.forms import ZeusProblemForm
from oioioi.zeus.models import ZeusProblemData


class ZeusProblemSource(UploadedPackageSource):
    key = 'zeus'
    short_description = _("Add Zeus problem")

    def __init__(self, zeus_instances=None):
        if zeus_instances is None:
            zeus_instances = [
                (zeus_id, '%s: %s' % (zeus_id, url))
                for zeus_id, (url, _login, _secret) in six.iteritems(
                    settings.ZEUS_INSTANCES
                )
            ]
        self.zeus_instances = zeus_instances

    def choose_backend(self, path, original_filename=None):
        return 'oioioi.zeus.package.ZeusPackageBackend'

    def create_env(
        self,
        user,
        contest,
        path,
        package,
        form,
        round_id=None,
        visibility=Problem.VISIBILITY_FRIENDS,
        existing_problem=None,
        original_filename=None,
    ):
        env = super(ZeusProblemSource, self).create_env(
            user,
            contest,
            path,
            package,
            form,
            round_id,
            visibility,
            existing_problem,
            original_filename,
        )
        env['zeus_id'] = form.cleaned_data['zeus_id']
        env['zeus_problem_id'] = form.cleaned_data['zeus_problem_id']
        # env['post_upload_handlers'].insert(0,
        #         'oioioi.zeus.handlers.save_zeus_data')
        return env

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
            return ZeusProblemForm(
                self.zeus_instances,
                contest,
                existing_problem,
                request.POST,
                request.FILES,
                initial=initial,
            )
        else:
            return ZeusProblemForm(
                self.zeus_instances, contest, existing_problem, initial=initial
            )
