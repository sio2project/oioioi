from django import forms
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Round, ProblemInstance
from oioioi.contests.utils import visible_rounds, visible_problem_instances
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

        categories = [('p_%d' % (pi.id,), _("Problem %s") % (pi.problem.name,))
                        for pi in visible_problem_instances(request)]
        categories += [('r_%d' % (round.id,), _("General, %s") % (round.name,))
                        for round in visible_rounds(request)]
        self.fields['category'].choices = categories

    def save(self, commit=True, *args, **kwargs):
        instance = super(AddContestMessageForm, self) \
                .save(commit=False, *args, **kwargs)
        instance.contest = self.request.contest
        if 'category' in self.cleaned_data:
            category = self.cleaned_data['category']
            type, sep, id = category.partition('_')
            if type == 'r':
                instance.round = \
                    Round.objects.get(contest=self.request.contest, id=id)
            elif type == 'p':
                instance.problem_instance = ProblemInstance.objects \
                    .get(contest=self.request.contest, id=id)
            else:
                raise ValueError(_("Unknown category type."))
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

