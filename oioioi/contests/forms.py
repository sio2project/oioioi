import json

from django import forms
from django.core.validators import RegexValidator
from django.contrib.admin import widgets
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.forms.widgets import Media as FormMedia
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from oioioi.base.forms import PublicMessageForm
from oioioi.base.utils.inputs import narrow_input_field, narrow_input_fields
from oioioi.base.utils.user_selection import UserSelectionField
from oioioi.contests.models import (
    Contest,
    ProblemInstance,
    Round,
    FilesMessage,
    SubmissionsMessage,
    SubmitMessage,
)
from oioioi.contests.utils import is_contest_basicadmin, submittable_problem_instances
from oioioi.programs.models import Test


class SimpleContestForm(forms.ModelForm):
    class Meta(object):
        model = Contest
        # Order of fields is important - focus after sending incomplete
        # form should not be on the 'name' field, otherwise the 'id' field,
        # as prepopulated with 'name' in ContestAdmin model, is cleared by
        # javascript with prepopulated fields functionality.
        fields = ['controller_name', 'name', 'id', 'school_year']

    start_date = forms.SplitDateTimeField(
        label=_("Start date"), widget=widgets.AdminSplitDateTime()
    )
    end_date = forms.SplitDateTimeField(
        required=False, label=_("End date"), widget=widgets.AdminSplitDateTime()
    )
    results_date = forms.SplitDateTimeField(
        required=False, label=_("Results date"), widget=widgets.AdminSplitDateTime()
    )

    def validate_years(year):
        year1 = int(year[:4])
        year2 = int(year[5:])
        if year1+1 != year2:
            raise ValidationError("The selected years must be consecutive.")

    school_year = forms.CharField(
        required=False, label=_("School year"), validators=[        
            RegexValidator(
                regex=r'^[0-9]{4}[/][0-9]{4}$',
                message="Enter a valid school year in the format 2021/2022.",
                code="invalid_school_year",
            ),
            validate_years,
            ]
    )

    def _generate_default_dates(self):
        now = timezone.now()
        self.initial['start_date'] = now
        self.initial['end_date'] = None
        self.initial['results_date'] = None

    def _set_dates(self, round):
        for date in ['start_date', 'end_date', 'results_date']:
            setattr(round, date, self.cleaned_data.get(date))

    def __init__(self, *args, **kwargs):
        super(SimpleContestForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance', None)
        if instance is not None:
            rounds = instance.round_set.all()
            if len(rounds) > 1:
                raise ValueError(
                    "SimpleContestForm does not support contests "
                    "with more than one round."
                )
            if len(rounds) == 1:
                round = rounds[0]
                self.initial['start_date'] = round.start_date
                self.initial['end_date'] = round.end_date
                self.initial['results_date'] = round.results_date
            else:
                self._generate_default_dates()
        else:
            self._generate_default_dates()

    def clean(self):
        cleaned_data = super(SimpleContestForm, self).clean()
        round = Round()
        self._set_dates(round)
        round.clean()
        return cleaned_data

    def save(self, commit=True):
        instance = super(SimpleContestForm, self).save(commit=False)
        rounds = instance.round_set.all()
        if len(rounds) > 1:
            raise ValueError(
                "SimpleContestForm does not support contests "
                "with more than one round."
            )
        if len(rounds) == 1:
            round = rounds[0]
        else:
            instance.save()
            round = Round(contest=instance, name=_("Round 1"))
        self._set_dates(round)
        round.save()

        if commit:
            instance.save()

        return instance


class ProblemInstanceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super(ProblemInstanceForm, self).__init__(*args, **kwargs)
        if instance and not instance.contest.is_archived:
            self.fields['round'].queryset = instance.contest.round_set
            self.fields['round'].required = True


class SubmissionForm(forms.Form):
    """Represents base submission form containing task selector.

    Recognized optional ``**kwargs`` fields:
      * ``problem_filter`` Function filtering submittable tasks.
      * ``kind`` Kind of submission accessible with ``kind`` property.
      * ``problem_instance`` When SubmissionForm is used only for one
          problem_instance. Otherwise ``problem_instance`` is None.
      * ``add_kind_and_user_fields`` Option deciding whether form should
          add kind and user fields to itself.
    """

    problem_instance_id = forms.ChoiceField(label=_("Problem"))

    _js = ['common/submit.js',]

    @property
    def media(self):
        return FormMedia(self._js)

    def __init__(self, request, *args, **kwargs):
        add_kind_and_user_fields = kwargs.pop('add_kind_and_user_fields', True)
        problem_instance = kwargs.pop('problem_instance', None)
        if problem_instance is None:
            # if problem_instance does not exist any from the current
            # contest is chosen. To change in future.
            # ALSO in mailsubmit.forms
            contest = request.contest
            assert contest is not None
            problem_instances = ProblemInstance.objects.filter(contest=contest)
            problem_instance = problem_instances[0]
        else:
            problem_instances = [problem_instance]
            contest = None
        self.all_problem_instances = problem_instances

        # Default kind is selected based on
        # the first problem_instance assigned to this form.
        # This is an arbitrary choice.
        self.kind = getattr(self, 'kind', None) or kwargs.pop(
            'kind',
            problem_instance.controller.get_default_submission_kind(
                request, problem_instance=problem_instance
            ),
        )
        problem_filter = kwargs.pop('problem_filter', None)
        self.request = request

        # taking the available problems
        pis = self.get_problem_instances()
        if problem_filter:
            pis = problem_filter(pis)
        pi_choices = [(pi.id, str(pi)) for pi in pis]

        # init form with previously sent data
        super(SubmissionForm, self).__init__(*args, **kwargs)

        # prepare problem instance selector
        pi_field = self.fields['problem_instance_id']
        self._set_field_show_always('problem_instance_id')

        if len(pi_choices) > 1:
            pi_field.choices = [('', '')] + pi_choices
        else:
            pi_field.choices = pi_choices

        narrow_input_field(pi_field)

        # if contest admin, add kind and 'as other user' field
        if add_kind_and_user_fields and contest and is_contest_basicadmin(request):
            self.fields['user'] = UserSelectionField(
                label=_("User"),
                hints_url=reverse(
                    'contest_user_hints', kwargs={'contest_id': request.contest.id}
                ),
                initial=request.user,
            )
            self._set_field_show_always('user')

            def clean_user():
                try:
                    user = self.cleaned_data['user']
                    if user == request.user:
                        return user
                    if not request.user.is_superuser:
                        contest.controller.registration_controller().filter_participants(
                            User.objects.filter(pk=user.pk)
                        ).get()
                    return user
                except User.DoesNotExist:
                    raise forms.ValidationError(
                        _("User does not exist or you do not have enough privileges")
                    )

            self.clean_user = clean_user
            self.fields['kind'] = forms.ChoiceField(
                choices=[('NORMAL', _("Normal")), ('IGNORED', _("Ignored"))],
                initial=self.kind,
                label=_("Kind"),
            )
            self._set_field_show_always('kind')
            narrow_input_fields([self.fields['kind'], self.fields['user']])

        self.hide_default_fields_pi_ids = []

        # adding additional fields, etc
        for pi in pis:
            pi.controller.adjust_submission_form(request, self, pi)

        self._set_default_fields_attributes()

        hide_default_fields_script = (
            "startShowingFields(" + json.dumps(self.hide_default_fields_pi_ids) + ")"
        )
        self.additional_scripts = [hide_default_fields_script]

        # fix field order:
        self.move_field_to_end('user')
        self.move_field_to_end('kind')

    def move_field_to_end(self, field_name):
        if field_name in self.fields:
            # delete field from fields and readdd it to put it at the end
            tmp = self.fields[field_name]
            del self.fields[field_name]
            self.fields[field_name] = tmp

    def set_custom_field_attributes(self, field_name, problem_instance):
        """
        Prepare custom field to be displayed only for a specific problems.
        Still all custom fields need to have unique names
        (best practice is to prefix them with `problem_instance.id`).
        :param field_name: Name of custom field
        :param problem_instance: Problem instance which they are assigned to
        """
        self.fields[field_name].widget.attrs['data-submit'] = str(problem_instance.id)

    def hide_default_fields(self, problem_instance):
        """
        Hide default form fields for a given problem instance.
        :param problem_instance: Problem instance which will have fields hidden
        """
        self.hide_default_fields_pi_ids.append(problem_instance.id)

    def _set_field_show_always(self, field_name):
        self.fields[field_name].widget.attrs['data-submit'] = 'always'

    def _set_default_fields_attributes(self):
        for field_name in self.fields:
            field = self.fields[field_name]
            if 'data-submit' not in field.widget.attrs:
                # If no attribute was set, set it to default.
                # This is for backwards compatibility with contests that
                # have only one submission form and don't need to bother.
                field.widget.attrs['data-submit'] = 'default'

    def get_problem_instances(self):
        return submittable_problem_instances(self.request)

    def is_valid(self):
        return forms.Form.is_valid(self)

    def clean(self, check_submission_limit=True, check_round_times=True):
        cleaned_data = super(SubmissionForm, self).clean()

        if 'kind' not in cleaned_data:
            cleaned_data['kind'] = self.kind

        if 'problem_instance_id' not in cleaned_data:
            return cleaned_data

        try:
            pi = ProblemInstance.objects.get(id=cleaned_data['problem_instance_id'])
            cleaned_data['problem_instance'] = pi
        except ProblemInstance.DoesNotExist:
            self._errors['problem_instance_id'] = self.error_class(
                [_("Invalid problem")]
            )
            del cleaned_data['problem_instance_id']
            return cleaned_data

        kind = cleaned_data['kind']
        if check_submission_limit and pi.controller.is_submissions_limit_exceeded(
            self.request, pi, kind
        ):
            raise ValidationError(
                _("Submission limit for the problem '%s' exceeded.")
                % pi.problem.name
            )

        decision = pi.controller.can_submit(self.request, pi, check_round_times)
        if not decision:
            raise ValidationError(str(getattr(decision, 'exc', _("Permission denied"))))

        return pi.controller.validate_submission_form(
            self.request, pi, self, cleaned_data
        )


class SubmissionFormForProblemInstance(SubmissionForm):
    def __init__(self, request, problem_instance, *args, **kwargs):
        self.problem_instance = problem_instance
        kwargs['problem_instance'] = problem_instance
        super(SubmissionFormForProblemInstance, self).__init__(request, *args, **kwargs)
        pis = self.fields['problem_instance_id']
        pis.widget.attrs['readonly'] = 'True'
        pis.widget.attrs['data-submit'] = 'hidden'

    def get_problem_instances(self):
        return [self.problem_instance]


class GetUserInfoForm(forms.Form):
    user = UserSelectionField(label=_("Username"))

    def __init__(self, request, *args, **kwargs):
        super(GetUserInfoForm, self).__init__(*args, **kwargs)
        self.fields['user'].hints_url = reverse(
            'contest_user_hints', kwargs={'contest_id': request.contest.id}
        )


class TestsSelectionForm(forms.Form):
    def __init__(self, request, queryset, pis_count, uses_is_active, *args, **kwargs):
        super(TestsSelectionForm, self).__init__(*args, **kwargs)
        problem_instance = queryset[0].problem_instance
        tests = Test.objects.filter(problem_instance=problem_instance, is_active=True)

        widget = forms.RadioSelect(attrs={'onChange': 'rejudgeTypeOnChange(this)'})
        self.fields['rejudge_type'] = forms.ChoiceField(widget=widget)
        if uses_is_active:
            self.fields['rejudge_type'].choices = [
                ('FULL', _("Rejudge submissions on all current active tests")),
                (
                    'NEW',
                    _(
                        "Rejudge submissions on active tests which "
                        "haven't been judged yet"
                    ),
                ),
            ]
        else:
            self.fields['rejudge_type'].choices = [
                ('FULL', _("Rejudge submissions on all tests"))
            ]

        self.initial['rejudge_type'] = 'FULL'

        if pis_count == 1:
            self.fields['rejudge_type'].choices.append(
                ('JUDGED', _("Rejudge submissions on judged tests only"))
            )

            self.fields['tests'] = forms.MultipleChoiceField(
                widget=forms.CheckboxSelectMultiple(attrs={'disabled': 'disabled'}),
                choices=[(test.name, test.name) for test in tests],
            )

        self.fields['submissions'] = forms.ModelMultipleChoiceField(
            widget=forms.CheckboxSelectMultiple, queryset=queryset, initial=queryset
        )


class FilesMessageForm(PublicMessageForm):
    class Meta(object):
        model = FilesMessage
        fields = ['content']


class SubmissionsMessageForm(PublicMessageForm):
    class Meta(object):
        model = SubmissionsMessage
        fields = ['content']


class SubmitMessageForm(PublicMessageForm):
    class Meta(object):
        model = SubmitMessage
        fields = ['content']


class SubmissionMessageForm(PublicMessageForm):
    class Meta(object):
        model = SubmitMessage
        fields = ['content']
