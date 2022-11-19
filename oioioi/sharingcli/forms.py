import json

import urllib.error
from django import forms
from django.core.validators import URLValidator
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from oioioi.problems.forms import ProblemUploadForm


class RemoteProblemForm(ProblemUploadForm):
    url = forms.CharField(label=_("Task URL"), validators=[URLValidator])

    def __init__(self, clients, *args, **kwargs):
        super(RemoteProblemForm, self).__init__(*args, **kwargs)
        self.clients = clients

        help_text = render_to_string('sharingcli/form-help.html', {'clients': clients})
        self.fields['url'].help_text = mark_safe(help_text)

    def clean_url(self):
        url = self.cleaned_data['url']
        for client in self.clients:
            if url.startswith(client.site_url):
                break
        else:
            raise forms.ValidationError(
                _("Only sites from the list below are acceptable")
            )

        try:
            # pylint: disable=undefined-loop-variable
            response = client.make_request('taskinfo', {'query': url}, timeout=10)
            response = json.loads(response.read())
            self.cleaned_data['client'] = client
            self.cleaned_data['task_id'] = response['id']
            return url
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise forms.ValidationError(_("Not a task URL"))
            else:
                raise forms.ValidationError(
                    _("Cannot connect to external site: %s") % (e,)
                )
        except Exception as e:
            raise forms.ValidationError(_("Invalid server response: %s") % (e,))
