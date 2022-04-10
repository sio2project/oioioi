import re
from collections import defaultdict

from django import forms
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.user_selection import UserSelectionField, UserSelectionWidget
from oioioi.contests.models import ProblemInstance
from oioioi.contests.utils import rounds_times
from oioioi.participants.models import Region
from oioioi.programs.models import Test

CONTEST_REPORT_KEY = 'all'


def _rounds(request):
    rounds = [(CONTEST_REPORT_KEY, _("All"))]
    rounds += [(str(r.id), r.name) for r in request.contest.round_set.all()]
    if len(rounds) == 1:
        # No rounds have visible results
        return []
    if len(rounds) == 2:
        # Only a single round => call this "contest report".
        return rounds[:1]
    return rounds


def _last_finished_round_id(request):
    past_rounds = [
        rt
        for rt in rounds_times(request, request.contest or None).items()
        if rt[1].is_past(request.timestamp)
    ]
    if not past_rounds:
        return None
    last_round = max(past_rounds, key=lambda x: x[1].end)
    return last_round[0].id


def _regions(request):
    res = [(CONTEST_REPORT_KEY, _("All"))]
    regions = Region.objects.filter(contest=request.contest)
    res += [(r.short_name, r.name) for r in regions]
    return res


def _testgroups(request):
    testgroups = []
    for round in request.contest.round_set.all():
        pis = ProblemInstance.objects.filter(round=round)
        res = {'id': str(round.id), 'name': round.name, 'tasks': []}
        for pi in pis:
            task = {
                'name': pi.problem.name,
                'short_name': pi.short_name,
                'testgroups': [],
            }
            for test in Test.objects.filter(problem_instance=pi):
                if test.group not in task['testgroups']:
                    task['testgroups'].append(test.group)
            res['tasks'].append(task)
        testgroups.append(res)
    return testgroups


report_types = (
    ('pdf_report', _("PDF")),
    ('xml_report', _("XML")),
)


class OIReportCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    def render(self, *args, **kwargs):
        output = super(OIReportCheckboxSelectMultiple, self).render(*args, **kwargs)
        return mark_safe(
            output.replace(u'<ul>', u'<ul class="unstyled">').replace(
                u'<label', u'<label class="checkbox"'
            )
        )


class OIReportForm(forms.Form):
    is_single_report = forms.BooleanField(required=False, label=_("Single report"))
    single_report_user = UserSelectionField(
        required=False,
        widget=UserSelectionWidget(attrs={'placeholder': _("User")}),
        label=_("Username"),
    )
    form_type = forms.ChoiceField(choices=report_types, label=_("Report type"))

    def __init__(self, request, *args, **kwargs):
        super(OIReportForm, self).__init__(*args, **kwargs)
        rounds = _rounds(request)
        last_finished_round_id = _last_finished_round_id(request)
        regions = _regions(request)
        testgroups = _testgroups(request)
        self.fields['report_round'] = forms.ChoiceField(
            choices=rounds, label=_("Round"), initial=last_finished_round_id
        )
        self.fields['report_region'] = forms.ChoiceField(
            choices=regions, label=_("Region")
        )

        self.fields['single_report_user'].hints_url = reverse(
            'get_report_users', kwargs={'contest_id': request.contest.id}
        )
        self.fields[
            'single_report_user'
        ].queryset = request.contest.controller.registration_controller().filter_participants(
            User.objects.all()
        )

        for round in testgroups:
            for task in round['tasks']:
                field_name = 'testgroup[%s]' % (task['short_name'])
                field_choices = [(group, group) for group in task['testgroups']]
                self.fields[field_name] = forms.MultipleChoiceField(
                    choices=field_choices,
                    widget=OIReportCheckboxSelectMultiple(),
                    label=task['short_name'],
                    required=False,
                )
                self.fields[field_name].round = round['id']

    def control_fields(self):
        for name in self.fields:
            if name.startswith('testgroup') or 'single' in name:
                continue
            else:
                yield self[name]

    def testgroup_fields(self):
        for name in self.fields:
            if name.startswith('testgroup'):
                yield self[name]
            else:
                continue

    def clean(self):
        cleaned_data = super(OIReportForm, self).clean()

        if cleaned_data['is_single_report']:
            report_user = cleaned_data.get('single_report_user')
            if report_user is None:
                self._errors['single_report_user'] = self.error_class(
                    [_("No user specified.")]
                )
                del cleaned_data['single_report_user']

        return cleaned_data

    def get_testgroups(self, request):
        testgroups = defaultdict(list)
        regex = re.compile(r'testgroup\[(.*)\]$')
        for field_name in self.fields:
            match = regex.match(field_name)
            if match:
                groups = self.cleaned_data[field_name]
                problem_instance = ProblemInstance.objects.get(
                    short_name=match.group(1), round__contest=request.contest
                )
                if groups:
                    testgroups[problem_instance] += groups
        return testgroups
