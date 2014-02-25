from django import forms
from oioioi.dashboard.models import DashboardMessage


class DashboardMessageForm(forms.ModelForm):
    class Meta(object):
        model = DashboardMessage
        fields = ['content']

    def __init__(self, request, *args, **kwargs):
        super(DashboardMessageForm, self).__init__(*args, **kwargs)
        self.fields['content'].widget \
                .attrs['class'] = 'input-xxlarge monospace'
        self.contest = request.contest

    def save(self, commit=True, *args, **kwargs):
        instance = super(DashboardMessageForm, self) \
                .save(commit=False, *args, **kwargs)
        instance.contest = self.contest
        if commit:
            instance.save()
        return instance
