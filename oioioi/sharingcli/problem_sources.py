import logging
import shutil
import tempfile
import urllib
import urllib2
from contextlib import contextmanager

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from oioioi.problems.problem_sources import PackageSource
from oioioi.sharingcli.forms import RemoteProblemForm
from oioioi.sharingcli.models import RemoteProblemURL

logger = logging.getLogger(__name__)


class RemoteClient(object):
    def __init__(self, site_url, sharing_url, client_id, client_secret):
        self.site_url = site_url
        self.sharing_url = sharing_url
        self.client_id = client_id
        self.client_secret = client_secret

    def make_request(self, relative_url, extra_data=None, **kwargs):
        url = self.sharing_url + '/' + relative_url
        post_data = {'client_id': self.client_id,
                'client_secret': self.client_secret}
        if not extra_data:
            extra_data = {}
        post_data.update(extra_data)
        return urllib2.urlopen(url, urllib.urlencode(post_data), **kwargs)


@contextmanager
def _file_from_request(request):
    f = tempfile.NamedTemporaryFile(suffix='.zip')
    shutil.copyfileobj(request, f)
    f.flush()
    yield f.name
    f.close()


class RemoteSource(PackageSource):
    key = 'ext'
    short_description = _("Add from external site")

    def __init__(self, clients=None):
        if clients is None:
            clients = [RemoteClient(*params) for params in
                    settings.SHARING_SERVERS]
        self.clients = clients

    def create_env(self, request, contest, form, path, package,
            existing_problem=None, original_filename=None):
        env = super(RemoteSource, self).create_env(request, contest, form,
                path, package, existing_problem, original_filename)
        env['url'] = form.cleaned_data['url']
        env['post_upload_handlers'] += ['oioioi.sharingcli.handlers.save_url']
        return env

    def get_package_file(self, request, contest, form, existing_problem=None):
        client = form.cleaned_data['client']
        response = client.make_request('task',
                {'task_id': form.cleaned_data['task_id']})
        return None, _file_from_request(response)

    def make_form(self, request, contest, existing_problem=None):
        initial = {}
        if existing_problem:
            try:
                initial = {'url': RemoteProblemURL.objects.get(
                            problem=existing_problem).url}
            except RemoteProblemURL.DoesNotExist:
                pass

        if request.method == 'POST':
            return RemoteProblemForm(self.clients, contest, existing_problem,
                    request.POST, request.FILES, initial=initial)
        else:
            return RemoteProblemForm(self.clients, contest, existing_problem,
                    initial=initial)
