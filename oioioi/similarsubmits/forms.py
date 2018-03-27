import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from oioioi.base.utils import find_closure
from oioioi.contests.models import Submission

similarity_pair_re = re.compile(
    r'(?P<submission_id>\d+):'
    r'(?P<username>[\w.@+-]+):'
    r'(?P<task>\w+)(?P<lang_ext>[\w.]+)')


class BulkAddSubmissionsSimilarityForm(forms.Form):
    similar_groups = forms.CharField(
        label=_("Similar groups"),
        widget=forms.Textarea(attrs={'class': 'input-xxlarge monospace'}),
        help_text=_(
            "Each line represents a group, submissions should be"
            " listed in format \"submission_id:username:task.lang\""
            " and separated by anything. Already existing groups won't"
            " be skipped!"
        )
    )
    find_transitive_closure = forms.BooleanField(required=False, initial=False,
            help_text=_("If any two submissions are marked as similar in the "
                        "input they will be put in one group.")
    )

    def __init__(self, request, *args, **kwargs):
        super(BulkAddSubmissionsSimilarityForm, self).__init__(*args, **kwargs)
        self.contest = request.contest

    def clean_similar_groups(self):
        data = self.cleaned_data['similar_groups'].splitlines()
        groups = []
        submissions_qs = Submission.objects \
                .filter(problem_instance__contest=self.contest) \
                .select_related('user', 'problem_instance')

        for line in data:
            matches = [m.groupdict()
                       for m in similarity_pair_re.finditer(line)]

            if len(matches) < 2:
                if line.strip():
                    raise ValidationError(_(
                            "Can't parse nonempty line:\n%(line)s")
                            % dict(line=line))
                else:
                    continue

            matched_submissions = []
            for match in matches:
                try:
                    submission = submissions_qs.get(id=match['submission_id'])
                except Submission.DoesNotExist:
                    raise ValidationError(
                        _("Submission %(id)s does not exists in line: "
                          "%(line)s") % dict(id=match['submission_id'],
                                             line=line))

                if submission.user is None:
                    raise ValidationError(
                        _("You can't say that this guy cooperated with model"
                          " solution author.... It's ridiculous! "
                          "In line: %(line)s") % dict(line=line))
                if submission.user.username != match['username']:
                    raise ValidationError(
                        _("Submission's %(id)s incorrect author:\n"
                          "Expected: %(expected)s, but got %(given)s"
                          " in line %(line)s." %
                          dict(id=match['submission_id'],
                               expected=submission.user.username,
                               given=match['username'], line=line)))

                matched_submissions.append(submission)

            groups.append(tuple(matched_submissions))

        if not groups:
            raise ValidationError(_("No group found in given data."))

        return groups

    def clean(self):
        cleaned_data = super(BulkAddSubmissionsSimilarityForm, self).clean()

        if 'similar_groups' in cleaned_data and \
                cleaned_data.get('find_transitive_closure'):
            cleaned_data['similar_groups'] = find_closure(
                    cleaned_data['similar_groups'])

        return cleaned_data
