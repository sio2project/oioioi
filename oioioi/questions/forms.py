from django import forms
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from oioioi.base.utils.user_selection import UserSelectionField
from oioioi.contests.models import Round, ProblemInstance
from oioioi.questions.models import message_kinds, Message, ReplyTemplate
from oioioi.questions.utils import get_categories, get_category


class AddContestMessageForm(forms.ModelForm):
    class Meta(object):
        model = Message
        fields = ['category', 'topic', 'content']

    category = forms.ChoiceField([], label=_("Category"))

    def __init__(self, request, *args, **kwargs):
        super(AddContestMessageForm, self).__init__(*args, **kwargs)
        self.fields['topic'].widget.attrs['class'] = 'input-xxlarge'
        self.fields['content'].widget.attrs['class'] = \
                'input-xxlarge monospace'

        self.request = request

        if 'instance' in kwargs:
            self.fields['category'].choices = get_categories(request)
            self.fields['category'].initial = get_category(kwargs['instance'])
        else:
            self.fields['category'].choices = \
                    [('', '')] + get_categories(request)

    def save(self, commit=True, *args, **kwargs):
        instance = super(AddContestMessageForm, self) \
                .save(commit=False, *args, **kwargs)
        instance.contest = self.request.contest
        if 'category' in self.cleaned_data:
            category = self.cleaned_data['category']
            type, _sep, id = category.partition('_')
            if type == 'r':
                instance.round = \
                    Round.objects.get(contest=self.request.contest, id=id)
                instance.problem_instance = None
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

    save_template = forms.BooleanField(required=False,
                                       widget=forms.HiddenInput,
                                       label=_("Save as template"))

    def __init__(self, *args, **kwargs):
        super(AddReplyForm, self).__init__(*args, **kwargs)
        del self.fields['category']
        self.fields['kind'].choices = \
                [c for c in message_kinds.entries if c[0] != 'QUESTION']

    def save(self, commit=True, *args, **kwargs):
        instance = super(AddReplyForm, self) \
                .save(commit=False, *args, **kwargs)
        if self.cleaned_data['save_template']:
            ReplyTemplate.objects.get_or_create(contest=instance.contest,
                                                content=instance.content)
        if commit:
            instance.save()
        return instance


class ChangeContestMessageForm(AddContestMessageForm):
    class Meta(object):
        model = Message
        fields = ['category', 'kind', 'topic', 'content']

    def __init__(self, kind, *args, **kwargs):
        super(ChangeContestMessageForm, self).__init__(*args, **kwargs)
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
    author = UserSelectionField(label=_("Author username"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(FilterMessageAdminForm, self).__init__(request, *args, **kwargs)
        self.fields['author'].hints_url = reverse('get_messages_authors',
            kwargs={'contest_id': request.contest.id})
