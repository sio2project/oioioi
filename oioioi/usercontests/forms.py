from django import forms

from oioioi.contests.forms import SimpleContestForm


class UserContestForm(SimpleContestForm):
    class Meta(SimpleContestForm.Meta):
        fields = ['name', 'id', 'default_submissions_limit', 'contact_email']
