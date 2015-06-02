from collections import OrderedDict

from django import forms
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from oioioi.base.utils.input_with_generate import TextInputWithGenerate
from oioioi.contests.models import ProblemStatementConfig
from oioioi.problems.models import ProblemSite, Tag, TagThrough


class ProblemUploadForm(forms.Form):
    contest_id = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, contest, existing_problem, *args, **kwargs):
        super(ProblemUploadForm, self).__init__(*args, **kwargs)
        self.round_id = None

        if contest and not existing_problem:
            choices = [(r.id, r.name) for r in contest.round_set.all()]
            if len(choices) >= 2:
                fields = self.fields.items()
                fields[0:0] = [('round_id', forms.ChoiceField(choices,
                        label=_("Round")))]
                self.fields = OrderedDict(fields)
            elif len(choices) == 1:
                self.round_id = choices[0][0]

    def clean(self):
        cleaned_data = super(ProblemUploadForm, self).clean()
        if self.round_id:
            cleaned_data['round_id'] = self.round_id
        return cleaned_data


class PackageUploadForm(ProblemUploadForm):
    package_file = forms.FileField(label=_("Package file"))


class ProblemStatementConfigForm(forms.ModelForm):
    class Meta(object):
        fields = '__all__'
        model = ProblemStatementConfig
        widgets = {
            'visible': forms.RadioSelect()
        }


class ProblemSiteForm(forms.ModelForm):
    class Meta(object):
        fields = ['url_key']
        model = ProblemSite
        widgets = {
            'url_key': TextInputWithGenerate()
        }


class ProblemsetSourceForm(forms.Form):
    url_key = forms.CharField(label=_("Problem's url key"), required=True)

    def __init__(self, url_key, *args, **kwargs):
        super(ProblemsetSourceForm, self).__init__(*args, **kwargs)
        if url_key:
            self.initial = {'url_key': url_key}


# TagSelectionWidget is designed to work with django-admin

class TagSelectionWidget(forms.Widget):
    html_template = "<div>" \
            "<input type=\"text\" autocomplete=\"off\" " \
            "id=\"%(id)s\" " \
            "name=\"%(name)s\" " \
            "onfocus=\"init_tag_addition(this.id, '%(data-hints-url)s')\" " \
            "value=\"%(value)s\" />" \
            "<span id=\"%(id)s-hints\" style=\"margin-left: 5px;\"></span>" \
            "</div>"

    def __init__(self, hints_url=None, *args, **kwargs):
        self.hints_url = hints_url
        super(TagSelectionWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        # Value can either be an integer (Tag's id) or a string (Tag's name)
        if value is None:
            value = ''
        elif isinstance(value, int):
            value = Tag.objects.get(id=value).name
        arguments = {
            'id': attrs['id'],
            'name': name,
            'value': value,
            'data-hints-url': reverse(self.hints_url),
        }
        return mark_safe(self.html_template % arguments)

    class Meta(object):
        js = ('common/tag_selection.js',)


class TagSelectionField(forms.ModelChoiceField):
    def __init__(self, data_hints_url):
        for field in Tag._meta.fields:
            if field.name == 'name':
                self.default_validators = field.validators
                break
        else:
            self.default_validators = []
        self.widget = TagSelectionWidget(data_hints_url)
        super(TagSelectionField, self).__init__(Tag.objects,
                to_field_name='name')

    def clean(self, value):
        for validator in self.default_validators:
            validator(value)
        return Tag.objects.get_or_create(name=value)[0]


class TagThroughForm(forms.ModelForm):
    tag = TagSelectionField('get_tag_hints')

    class Meta(object):
        fields = ['problem']
        model = TagThrough
