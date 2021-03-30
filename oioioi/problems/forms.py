from collections import OrderedDict

from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import transaction
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils.input_with_generate import TextInputWithGenerate
from oioioi.base.utils.inputs import narrow_input_field
from oioioi.contests.models import ProblemStatementConfig, RankingVisibilityConfig
from oioioi.problems.models import (
    AlgorithmTag,
    AlgorithmTagThrough,
    DifficultyTag,
    DifficultyTagThrough,
    OriginInfoValue,
    Problem,
    ProblemSite,
    Tag,
    TagThrough,
)


class ProblemUploadForm(forms.Form):
    contest_id = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, contest, existing_problem, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ProblemUploadForm, self).__init__(*args, **kwargs)
        self.round_id = None
        self.visibility = None

        if contest and not existing_problem:
            choices = [(r.id, r.name) for r in contest.round_set.all()]
            if len(choices) >= 2:
                fields = list(self.fields.items())
                fields[0:0] = [
                    ('round_id', forms.ChoiceField(choices, label=_("Round")))
                ]
                self.fields = OrderedDict(fields)
            elif len(choices) == 1:
                self.round_id = choices[0][0]

        if 'oioioi.problemsharing' in settings.INSTALLED_APPS and not existing_problem:
            if user and user.has_perm('teachers.teacher'):
                choices = [
                    (Problem.VISIBILITY_FRIENDS, 'Friends'),
                    (Problem.VISIBILITY_PRIVATE, 'Private'),
                    (Problem.VISIBILITY_PUBLIC, 'Public'),
                ]
                default_visibility = Problem.VISIBILITY_FRIENDS
                if contest:
                    last_problem = (
                        Problem.objects.filter(contest=contest, author=user)
                        .order_by('-id')
                        .first()
                    )
                    if (
                        last_problem
                        and last_problem.visibility == Problem.VISIBILITY_PRIVATE
                    ):
                        default_visibility = Problem.VISIBILITY_PRIVATE

                self.initial.update({'visibility': default_visibility})
                self.fields.update(
                    {
                        'visibility': forms.ChoiceField(
                            choices,
                            label=_("Visibility"),
                            required=True,
                            initial=default_visibility,
                        )
                    }
                )

    def clean(self):
        cleaned_data = super(ProblemUploadForm, self).clean()
        if self.round_id:
            cleaned_data['round_id'] = self.round_id
        if self.visibility:
            cleaned_data['visibility'] = self.visibility
        return cleaned_data


class PackageUploadForm(ProblemUploadForm):
    package_file = forms.FileField(label=_("Package file"))


class ProblemStatementConfigForm(forms.ModelForm):
    class Meta(object):
        fields = '__all__'
        model = ProblemStatementConfig
        widgets = {'visible': forms.RadioSelect()}


class RankingVisibilityConfigForm(forms.ModelForm):
    class Meta(object):
        fields = '__all__'
        model = RankingVisibilityConfig
        widgets = {'visible': forms.RadioSelect()}


class ProblemSiteForm(forms.ModelForm):
    class Meta(object):
        fields = ['url_key']
        model = ProblemSite
        widgets = {'url_key': TextInputWithGenerate()}


class ProblemsetSourceForm(forms.Form):
    url_key = forms.CharField(label=_("Enter problem's secret key"), required=True)

    def __init__(self, url_key, *args, **kwargs):
        super(ProblemsetSourceForm, self).__init__(*args, **kwargs)
        if url_key:
            self.initial = {'url_key': url_key}


class ProblemStatementReplaceForm(forms.Form):
    file_name = forms.ChoiceField(label=_("Statement filename"))
    file_replacement = forms.FileField(label=_("Replacement file"), required=True)

    def __init__(self, file_names, *args, **kwargs):
        super(ProblemStatementReplaceForm, self).__init__(*args, **kwargs)
        upload_file_field = self.fields['file_replacement']
        file_name_field = self.fields['file_name']
        file_name_field.choices = [('', '')] + [(name, name) for name in file_names]
        self._set_field_show_always('file_name')
        narrow_input_field(file_name_field)
        narrow_input_field(upload_file_field)
        self.initial.update({'file_name': ''})

    def _set_field_show_always(self, field_name):
        self.fields[field_name].widget.attrs['data-submit'] = 'always'


class PackageFileReuploadForm(forms.Form):
    file_name = forms.ChoiceField(label=_("File name"))
    file_replacement = forms.FileField(label=_("Replacement file"), required=False)

    def __init__(self, file_names, *args, **kwargs):
        super(PackageFileReuploadForm, self).__init__(*args, **kwargs)
        upload_file_field = self.fields['file_replacement']
        file_name_field = self.fields['file_name']
        file_name_field.choices = [('', '')] + [(name, name) for name in file_names]
        self._set_field_show_always('file_name')
        narrow_input_field(file_name_field)
        narrow_input_field(upload_file_field)
        self.initial.update({'file_name': ''})

    def _set_field_show_always(self, field_name):
        self.fields[field_name].widget.attrs['data-submit'] = 'always'


class LocalizationFormset(forms.models.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.min_num = len(settings.LANGUAGES)
        self.max_num = len(settings.LANGUAGES)
        kwargs['initial'] = [
            {'language': lang[0]}
            for lang in settings.LANGUAGES
            if not kwargs['instance'].localizations.filter(language=lang[0]).exists()
        ]
        super(LocalizationFormset, self).__init__(*args, **kwargs)


# TagSelectionWidget is designed to work with django-admin


class TagSelectionWidget(forms.Widget):
    html_template = (
        "<div>"
        "<input type=\"text\" autocomplete=\"off\" "
        "id=\"%(id)s\" "
        "name=\"%(name)s\" "
        "onfocus=\"init_tag_addition(this.id, '%(data-hints-url)s')\" "
        "value=\"%(value)s\" />"
        "<span id=\"%(id)s-hints\" style=\"margin-left: 5px;\"></span>"
        "</div>"
    )

    def __init__(self, tag_cls, hints_url=None, *args, **kwargs):
        self.tag_cls = tag_cls
        self.hints_url = hints_url
        super(TagSelectionWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        # check if this is the default renderer
        if renderer is not None and not isinstance(
            renderer, forms.renderers.DjangoTemplates
        ):
            raise AssertionError
        # Value can either be an integer (Tag's id) or a string (Tag's name)
        if value is None:
            value = ''
        elif isinstance(value, int):
            value = self.tag_cls.objects.get(id=value).name
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
    def __init__(self, tag_cls, data_hints_url):
        self.tag_cls = tag_cls
        for field in tag_cls._meta.fields:
            if field.name == 'name':
                self.default_validators = field.validators
                break
        else:
            self.default_validators = []
        self.widget = TagSelectionWidget(tag_cls, data_hints_url)
        super(TagSelectionField, self).__init__(
            self.tag_cls.objects, to_field_name='name'
        )

    def clean(self, value):
        for validator in self.default_validators:
            validator(value)
        return self.tag_cls.objects.get_or_create(name=value)[0]


class OriginInfoValueForm(forms.ModelForm):
    @transaction.atomic
    def save(self, commit=True):
        instance = super(OriginInfoValueForm, self).save(commit=False)

        # Ensure parent_tag exists on problems
        category = self.cleaned_data['category']
        parent_tag = category.parent_tag
        instance.parent_tag = parent_tag
        problems = self.cleaned_data.get('problems').prefetch_related('origintag_set')
        for problem in problems:
            if parent_tag not in problem.origintag_set.all():
                parent_tag.problems.add(problem)

        if commit:
            instance.save()
        return instance

    class Meta(object):
        model = OriginInfoValue
        fields = ('category', 'value', 'order', 'problems')
        exclude = ('parent_tag',)


class OriginTagThroughForm(forms.ModelForm):
    class Meta(object):
        labels = {'origintag': _("Origin Tag")}
        help_texts = {
            'origintag': _(
                "Origin tags inform about the problem's general origin - e.g. a specific competition, olympiad, or programming camp."
            )
        }


class OriginInfoValueThroughForm(forms.ModelForm):
    class Meta(object):
        labels = {'origininfovalue': _("Origin Information")}
        help_texts = {
            'origininfovalue': _(
                "Origin information values inform about the problem's specific origin - a year, round, day, etc."
            )
        }


class DifficultyTagThroughForm(forms.ModelForm):
    tag = TagSelectionField(DifficultyTag, 'get_difficultytag_hints')

    class Meta(object):
        fields = ['problem']
        model = DifficultyTagThrough


class AlgorithmTagThroughForm(forms.ModelForm):
    tag = TagSelectionField(AlgorithmTag, 'get_algorithmtag_hints')

    class Meta(object):
        fields = ['problem']
        model = AlgorithmTagThrough


class TagThroughForm(forms.ModelForm):
    tag = TagSelectionField(Tag, 'get_tag_hints')

    class Meta(object):
        fields = ['problem']
        model = TagThrough
