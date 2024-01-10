from collections import OrderedDict

from django import forms
from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from oioioi.base.utils.input_with_generate import TextInputWithGenerate
from oioioi.base.utils.inputs import narrow_input_field
from oioioi.contests.models import ProblemStatementConfig, RankingVisibilityConfig, RegistrationAvailabilityConfig
from oioioi.problems.models import OriginInfoValue, Problem, ProblemSite


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
                    ('round_id', forms.ChoiceField(choices=choices, label=_("Round")))
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
                            choices=choices,
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


class RegistrationAvailabilityConfigForm(forms.ModelForm):
    class Meta(object):
        fields = '__all__'
        model = RegistrationAvailabilityConfig
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


def _localized_formset_get_initial(localized_objects):
    return [
        {'language': lang[0]}
        for lang in settings.LANGUAGES
        if not localized_objects.filter(language=lang[0]).exists()
    ]


class ProblemNameInlineFormSet(forms.models.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        kwargs['initial'] = _localized_formset_get_initial(kwargs['instance'].names)
        super(ProblemNameInlineFormSet, self).__init__(*args, **kwargs)
        self.max_num = len(settings.LANGUAGES)


class LocalizationFormset(forms.models.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        if kwargs['instance'].pk:
            kwargs['initial'] = _localized_formset_get_initial(
                kwargs['instance'].localizations
            )
        super(LocalizationFormset, self).__init__(*args, **kwargs)
        self.min_num = self.max_num = len(settings.LANGUAGES)
        for form in self.forms:
            form.empty_permitted = False


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


def _label_from_instance(obj):
    return obj.full_name


class OriginTagThroughForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(OriginTagThroughForm, self).__init__(*args, **kwargs)
        self.fields['origintag'].label_from_instance = _label_from_instance

    class Meta(object):
        labels = {'origintag': _("Origin Tag")}
        help_texts = {
            'origintag': _(
                "Origin tags inform about the problem's general origin "
                "- e.g. a specific competition, olympiad, or programming camp."
            )
        }


class OriginInfoValueThroughForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(OriginInfoValueThroughForm, self).__init__(*args, **kwargs)
        self.fields['origininfovalue'].label_from_instance = _label_from_instance

    class Meta(object):
        labels = {'origininfovalue': _("Origin Information")}
        help_texts = {
            'origininfovalue': _(
                "Origin information values inform about the problem's specific origin"
                "- a year, round, day, etc."
            )
        }


class DifficultyTagThroughForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(DifficultyTagThroughForm, self).__init__(*args, **kwargs)
        self.fields['tag'].label_from_instance = _label_from_instance

    class Meta(object):
        labels = {'tag': _("Difficulty Tag")}
        help_texts = {
            'tag': _(
                "Most problems fall into the 'Easy' and 'Medium' category. "
                "However, there are problems that are meant for learning "
                "the basics of programming (these are 'Very easy') and those "
                "that are 'Hard' and exceptionally hard - the latter fall "
                "into the 'Very hard' category."
            )
        }


class AlgorithmTagThroughForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AlgorithmTagThroughForm, self).__init__(*args, **kwargs)
        self.fields['tag'].label_from_instance = _label_from_instance

    class Meta(object):
        labels = {'tag': _("Algorithm Tag")}
        help_texts = {
            'tag': _(
                "Algorithm tags inform about the algorithms, theorems "
                "and data structures needed to solve a problem. "
                "Algorithm tags can also inform about the type of a "
                "problem, e.g. if a problem is a quiz."
            )
        }
