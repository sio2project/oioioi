from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Round, ProblemInstance
from oioioi.questions.models import message_kinds, Message
from oioioi.questions.utils import get_categories


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

        self.fields['category'].choices = get_categories(request)

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


class ChangeContestMessageForm(AddContestMessageForm):
    class Meta:
        model = Message
        fields = ['kind', 'topic', 'content']

    def __init__(self, kind, *args, **kwargs):
        super(ChangeContestMessageForm, self).__init__(*args, **kwargs)
        del self.fields['category']
        if kind == 'QUESTION':
            self.fields['kind'].choices = \
                [c for c in message_kinds.entries if c[0] == 'QUESTION']
        else:
            self.fields['kind'].choices = \
                [c for c in message_kinds.entries if c[0] != 'QUESTION']


class FilterMessageForm(forms.Form):
    category = forms.ChoiceField([], label=_("Category"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(FilterMessageForm, self).__init__(*args, **kwargs)
        choices = get_categories(request)
        choices.insert(0, ('all', _("All")))
        self.fields['category'].choices = choices

    def clean_category(self):
        category = self.cleaned_data['category']
        type, _, id = category.partition('_')
        return type, id


class FilterMessageAdminForm(FilterMessageForm):
    author = forms.CharField(label=_("Author username"), required=False)

    def clean_author(self):
        username = self.cleaned_data['author'].split()
        if username:
            # We allow fill 'author' form area only by username typed directly
            # or by full name chosen from typeahead.
            if len(username) == 1 or (len(username) and
                    username[1].startswith('(') and username[-1].endswith(')')):
                username = username[0]

                try:
                    return User.objects.get(username=username)
                except User.DoesNotExist:
                    raise forms.ValidationError(_("'%s' is invalid username."
                                                  % username))
            else:
                raise forms.ValidationError(
                    _("Type username directly or choose suggested full name."))

        else:
            return None
