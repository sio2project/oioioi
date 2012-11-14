from django import forms
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import ProblemInstance
from oioioi.contests.utils import visible_problem_instances
from oioioi.questions.models import message_kinds, Message

class AddContestMessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['category', 'topic', 'content']

    category = forms.ChoiceField([], label=_("Category"))

    def __init__(self, request, *args, **kwargs):
        super(AddContestMessageForm, self).__init__(*args, **kwargs)
        self.fields['topic'].widget.attrs['class'] = 'input-xxlarge'
        self.fields['content'].widget.attrs['class'] = 'input-xxlarge monospace'

        self.request = request

        problem_instances = visible_problem_instances(request)
        categories = [('__general__', _("General"))] + \
                [(pi.id, _("Problem %s") % (pi.problem.name,))
                        for pi in problem_instances]
        self.fields['category'].choices = categories

    def save(self, commit=True, *args, **kwargs):
        instance = super(AddContestMessageForm, self) \
                .save(commit=False, *args, **kwargs)
        instance.contest = self.request.contest
        if 'category' in self.cleaned_data:
            category = self.cleaned_data['category']
            if category != '__general__':
                instance.problem_instance = \
                        ProblemInstance.objects.get(
                                contest=self.request.contest, id=category)
        if commit:
            instance.save()
        return instance

class AddReplyForm(AddContestMessageForm):
    class Meta(AddContestMessageForm.Meta):
        fields = ['kind', 'topic', 'content']

    def __init__(self, *args, **kwargs):
        super(AddReplyForm, self).__init__(*args, **kwargs)
        del self.fields['category']
        self.fields['kind'].choices = \
                [c for c in message_kinds.entries if c[0] != 'QUESTION']


