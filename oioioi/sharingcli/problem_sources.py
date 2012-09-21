from django.conf import settings
from django.core.validators import URLValidator
from django import forms
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from oioioi.problems.models import Problem
from oioioi.problems.problem_sources import PackageSource
from oioioi.sharingcli.models import RemoteProblemURL
import json
import logging
import urllib
import urllib2
import tempfile
import shutil

logger = logging.getLogger(__name__)

class RemoteClient(object):
    def __init__(self, site_url, sharing_url, client_id, client_secret):
        self.site_url = site_url
        self.sharing_url = sharing_url
        self.client_id = client_id
        self.client_secret = client_secret

    def make_request(self, relative_url, extra_data={}, **kwargs):
        url = self.sharing_url + '/' + relative_url
        post_data = {'client_id': self.client_id,
                'client_secret': self.client_secret}
        post_data.update(extra_data)
        return urllib2.urlopen(url, urllib.urlencode(post_data), **kwargs)

class RemoteProblemForm(forms.Form):
    url = forms.CharField(
            label=_("Task URL"),
            widget=forms.TextInput(attrs={'class': 'input-xxlarge'}),
            validators=[URLValidator])

    def __init__(self, clients, *args, **kwargs):
        super(RemoteProblemForm, self).__init__(*args, **kwargs)
        self.clients = clients

        help_text = render_to_string('sharingcli/form_help_text.html',
                {'clients': clients})
        self.fields['url'].help_text = mark_safe(help_text)

    def clean_url(self):
        url = self.cleaned_data['url']
        for client in self.clients:
            if url.startswith(client.site_url):
                break
        else:
            raise forms.ValidationError(_("Only sites from the list below are "
                "acceptable"))

        try:
            response = client.make_request('taskinfo', {'query': url},
                    timeout=10)
            response = json.loads(response.read())
            self.cleaned_data['client'] = client
            self.cleaned_data['task_id'] = response['id']
            return url
        except urllib2.HTTPError, e:
            if e.code == 404:
                raise forms.ValidationError(_("Not a task URL"))
            else:
                raise forms.ValidationError(_("Cannot connect to external "
                    "site: %s") % (e,))
        except Exception, e:
            raise forms.ValidationError(_("Invalid server response: %s") %
                    (e,))

class RemoteSource(PackageSource):
    key = 'ext'
    short_description = _("Add from external site")

    def __init__(self, clients=None):
        if clients is None:
            clients = [RemoteClient(*params) for params in
                    settings.SHARING_SERVERS]
        self.clients = clients

    def process_valid_form(self, request, contest, form,
            existing_problem=None):
        client = form.cleaned_data['client']
        response = client.make_request('task',
                {'task_id': form.cleaned_data['task_id']})
        with tempfile.NamedTemporaryFile(suffix='.zip') as f:
            shutil.copyfileobj(response, f)
            f.flush()
            problem = self.process_package(request, contest, f.name,
                    f.name, existing_problem)
            if isinstance(problem, Problem):
                purl, created = RemoteProblemURL.objects.get_or_create(
                        problem=problem)
                purl.url = form.cleaned_data['url']
                purl.save()
            return problem

    def make_form(self, request, contest, existing_problem=None):
        initial = {}
        if existing_problem:
            try:
                initial = {'url': RemoteProblemURL.objects.get(
                            problem=existing_problem).url}
            except RemoteProblemURL.DoesNotExist:
                pass

        if request.method == 'POST':
            return RemoteProblemForm(self.clients, request.POST, request.FILES,
                    initial=initial)
        else:
            return RemoteProblemForm(self.clients, initial=initial)

    def view(self, request, contest, existing_problem=None):
        form = self.make_form(request, contest, existing_problem)
        if request.method == 'POST':
            if form.is_valid():
                try:
                    return self.process_valid_form(request, contest, form,
                            existing_problem)
                except Exception, e:
                    logger.error("Error processing package", exc_info=True)
                    form._errors['__all__'] = form.error_class([unicode(e)])
        return TemplateResponse(request, 'problems/package_source.html',
                {'form': form})
