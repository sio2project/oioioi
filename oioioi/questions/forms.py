from django import forms
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from oioioi.base.forms import PublicMessageForm
from oioioi.base.utils.inputs import narrow_input_field
from oioioi.base.utils.user_selection import UserSelectionField
from oioioi.base.widgets import DateTimePicker
from oioioi.contests.models import ProblemInstance, Round
from oioioi.contests.utils import is_contest_basicadmin
from oioioi.questions.models import (
    Message,
    ReplyTemplate,
    message_kinds,
    NewsMessage,
    AddQuestionMessage,
)
from oioioi.questions.utils import get_categories, get_category


class AddContestMessageForm(forms.ModelForm):
    class Meta(object):
        model = Message
        fields = ['category', 'topic', 'content', 'pub_date']
        help_texts = {'pub_date': _("Leave empty for immediate publication")}

    category = forms.ChoiceField(choices=[], label=_("Category"))

    def __init__(self, request, *args, **kwargs):
        super(AddContestMessageForm, self).__init__(*args, **kwargs)
        self.fields['content'].widget.attrs['class'] = 'monospace'

        if not is_contest_basicadmin(request):
            del self.fields['pub_date']
        else:
            self.fields['pub_date'].widget = DateTimePicker()
            self.fields['pub_date'].initial = timezone.now()
            # DateTimePicker is always narrow,
            # we don't mark it manually

        self.request = request

        instance = kwargs.get('instance', None)
        if instance is not None:
            self.fields['category'].choices = get_categories(request)
            self.fields['category'].initial = get_category(instance)
        else:
            self.fields['category'].choices = [('', '')] + get_categories(request)

    def save(self, commit=True, *args, **kwargs):
        instance = super(AddContestMessageForm, self).save(
            commit=False, *args, **kwargs
        )
        instance.contest = self.request.contest
        if 'category' in self.cleaned_data:
            category = self.cleaned_data['category']
            type, _sep, id = category.partition('_')
            if type == 'r':
                instance.round = Round.objects.get(contest=self.request.contest, id=id)
                instance.problem_instance = None
            elif type == 'p':
                instance.problem_instance = ProblemInstance.objects.get(
                    contest=self.request.contest, id=id
                )
            else:
                raise ValueError(_("Unknown category type."))
        if commit:
            instance.save()
        return instance


class AddReplyForm(AddContestMessageForm):
    class Meta(AddContestMessageForm.Meta):
        fields = ['kind', 'topic', 'content', 'pub_date']

    save_template = forms.BooleanField(
        required=False, widget=forms.HiddenInput, label=_("Save as template")
    )

    def __init__(self, *args, **kwargs):
        super(AddReplyForm, self).__init__(*args, **kwargs)
        del self.fields['category']
        self.fields['kind'].choices = [
            c for c in message_kinds.entries if c[0] != 'QUESTION'
        ]
        narrow_input_field(self.fields['kind'])

    def save(self, commit=True, *args, **kwargs):
        instance = super(AddReplyForm, self).save(commit=False, *args, **kwargs)
        if self.cleaned_data['save_template']:
            ReplyTemplate.objects.get_or_create(
                contest=instance.contest, content=instance.content
            )
        if commit:
            instance.save()
        return instance


class ChangeContestMessageForm(AddContestMessageForm):
    class Meta(AddContestMessageForm.Meta):
        fields = ['category', 'kind', 'topic', 'content', 'pub_date']

    def __init__(self, kind, *args, **kwargs):
        super(ChangeContestMessageForm, self).__init__(*args, **kwargs)
        if kind == 'QUESTION':
            self.fields['kind'].choices = [
                c for c in message_kinds.entries if c[0] == 'QUESTION'
            ]
        else:
            self.fields['kind'].choices = [
                c for c in message_kinds.entries if c[0] != 'QUESTION'
            ]


class FilterMessageForm(forms.Form):
    TYPE_ALL_MESSAGES = 'all'
    TYPE_PUBLIC_ANNOUNCEMENTS = 'public'
    TYPE_ALL_CATEGORIES = 'all'

    message_type = forms.ChoiceField(
        choices=[
            (TYPE_ALL_MESSAGES, _("All message types")),
            (TYPE_PUBLIC_ANNOUNCEMENTS, _("Public announcements")),
        ],
        label=_("Message type"),
        required=False,
    )
    category = forms.ChoiceField(choices=[], label=_("Category"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(FilterMessageForm, self).__init__(*args, **kwargs)
        choices = get_categories(request)
        choices.insert(0, (self.TYPE_ALL_CATEGORIES, _("All categories")))
        self.fields['category'].choices = choices


class FilterMessageAdminForm(FilterMessageForm):
    author = UserSelectionField(label=_("Author username"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(FilterMessageAdminForm, self).__init__(request, *args, **kwargs)
        self.fields['author'].hints_url = reverse(
            'get_messages_authors', kwargs={'contest_id': request.contest.id}
        )
        self.fields['author'].widget.attrs['placeholder'] = _("Author username")


class NewsMessageForm(PublicMessageForm):
    class Meta(object):
        model = NewsMessage
        fields = ['content']


class AddQuestionMessageForm(PublicMessageForm):
    class Meta(object):
        model = AddQuestionMessage
        fields = ['content']
