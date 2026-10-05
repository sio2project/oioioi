from django import forms
from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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
    AddQuestionMessage,
    Message,
    NewsMessage,
    ReplyTemplate,
    message_kinds,
)
from oioioi.questions.utils import get_categories, get_category


def get_active_contest_participants(request):
    if not apps.is_installed("oioioi.participants"):
        return User.objects.none()
    return User.objects.filter(participant__contest=request.contest, participant__status="ACTIVE").distinct()


def get_selected_private_message_recipients(request, recipient, groups):
    active_participants = get_active_contest_participants(request)
    recipients = active_participants.filter(usergroups__in=groups) if groups else User.objects.none()
    if recipient is not None:
        recipients = recipients | active_participants.filter(id=recipient.id)
    return recipients.distinct()


class AddContestMessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["category", "topic", "content", "pub_date"]
        help_texts = {"pub_date": _("Leave empty for immediate publication")}

    category = forms.ChoiceField(choices=[], label=_("Category"))

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"].widget.attrs["class"] = "monospace"

        if not is_contest_basicadmin(request):
            del self.fields["pub_date"]
        else:
            self.fields["pub_date"].widget = DateTimePicker()
            self.fields["pub_date"].initial = timezone.now()
            # DateTimePicker is always narrow,
            # we don't mark it manually

        self.request = request

        instance = kwargs.get("instance", None)
        if instance is not None:
            self.fields["category"].choices = get_categories(request)
            self.fields["category"].initial = get_category(instance)
        else:
            self.fields["category"].choices = [("", "")] + get_categories(request)

    def save(self, commit=True, *args, **kwargs):
        instance = super().save(commit=False, *args, **kwargs)
        instance.contest = self.request.contest
        if "category" in self.cleaned_data:
            category = self.cleaned_data["category"]
            type, _sep, id = category.partition("_")
            if type == "r":
                instance.round = Round.objects.get(contest=self.request.contest, id=id)
                instance.problem_instance = None
            elif type == "p":
                instance.problem_instance = ProblemInstance.objects.get(contest=self.request.contest, id=id)
            else:
                raise ValueError(_("Unknown category type."))
        if commit:
            instance.save()
        return instance


class AddReplyForm(AddContestMessageForm):
    class Meta(AddContestMessageForm.Meta):
        fields = ["kind", "topic", "content", "pub_date"]

    save_template = forms.BooleanField(required=False, widget=forms.HiddenInput, label=_("Save as template"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields["category"]
        self.fields["kind"].choices = [c for c in message_kinds.entries if c[0] != "QUESTION"]
        narrow_input_field(self.fields["kind"])

    def save(self, commit=True, *args, **kwargs):
        instance = super().save(commit=False, *args, **kwargs)
        if self.cleaned_data["save_template"]:
            ReplyTemplate.objects.get_or_create(contest=instance.contest, content=instance.content)
        if commit:
            instance.save()
        return instance


class AddPrivateReplyForm(AddReplyForm):
    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["kind"].choices = [("PRIVATE", message_kinds["PRIVATE"])]
        self.fields["kind"].initial = "PRIVATE"
        self.fields["kind"].widget = forms.HiddenInput()
        self.fields.pop("pub_date", None)
        if not is_contest_basicadmin(request):
            self.fields.pop("save_template")

    def save(self, *args, **kwargs):
        self.cleaned_data.setdefault("save_template", False)
        return super().save(*args, **kwargs)


class PrivateMessageFormMixin:
    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.active_participants = get_active_contest_participants(request)
        self.fields["recipient"].queryset = self.active_participants
        self.fields["recipient"].hints_url = reverse("get_private_message_recipients", kwargs={"contest_id": request.contest.id})
        if apps.is_installed("oioioi.usergroups"):
            from oioioi.usergroups.models import UserGroup

            self.fields["groups"].queryset = UserGroup.objects.filter(contests=request.contest).order_by("name")
        else:
            self.fields.pop("groups")
        self._replace_recipients = False
        self._recipient_ids = []

        instance = kwargs.get("instance")
        self.recipients_frozen = bool(instance and instance.pk and (instance.pub_date is None or instance.pub_date <= request.timestamp))
        if instance and instance.pk:
            recipients = instance.recipients.all()
            if recipients.count() == 1:
                self.fields["recipient"].initial = recipients.first()
        if self.recipients_frozen:
            self.fields["recipient"].disabled = True
            if "groups" in self.fields:
                self.fields["groups"].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        if self.recipients_frozen:
            if self.is_bound and ("recipient" in self.data or "groups" in self.data):
                raise ValidationError(_("Recipients cannot be changed after publication."))
            return cleaned_data

        recipient = cleaned_data.get("recipient")
        groups = cleaned_data.get("groups")
        if not recipient and not groups:
            if self.instance.pk:
                return cleaned_data
            raise ValidationError(_("Select at least one participant or group."))

        recipients = get_selected_private_message_recipients(self.request, recipient, groups)
        self._recipient_ids = list(recipients.values_list("id", flat=True))
        if not self._recipient_ids:
            raise ValidationError(_("The selected groups contain no active participants."))
        self._replace_recipients = True
        return cleaned_data

    def save_recipients(self, instance):
        if self._replace_recipients:
            instance.recipients.set(self._recipient_ids)


class AddPrivateMessageForm(PrivateMessageFormMixin, AddContestMessageForm):
    recipient = UserSelectionField(label=_("Participant"), required=False)
    groups = forms.ModelMultipleChoiceField(queryset=User.objects.none(), label=_("Groups"), required=False)

    class Meta(AddContestMessageForm.Meta):
        fields = ["category", "recipient", "groups", "topic", "content", "pub_date"]


class ChangeContestMessageForm(AddContestMessageForm):
    class Meta(AddContestMessageForm.Meta):
        fields = ["category", "kind", "topic", "content", "pub_date"]

    def __init__(self, kind, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kind == "QUESTION":
            self.fields["kind"].choices = [c for c in message_kinds.entries if c[0] == "QUESTION"]
        else:
            self.fields["kind"].choices = [c for c in message_kinds.entries if c[0] != "QUESTION"]


class ChangePrivateMessageForm(AddPrivateMessageForm):
    class Meta(AddPrivateMessageForm.Meta):
        fields = ["category", "kind", "recipient", "groups", "topic", "content", "pub_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].choices = [("PRIVATE", message_kinds["PRIVATE"])]
        narrow_input_field(self.fields["kind"])


class ChangePrivateReplyForm(ChangeContestMessageForm):
    def __init__(self, *args, **kwargs):
        super().__init__("PRIVATE", *args, **kwargs)
        self.fields["kind"].choices = [("PRIVATE", message_kinds["PRIVATE"])]


class FilterMessageForm(forms.Form):
    TYPE_ALL_MESSAGES = "all"
    TYPE_PUBLIC_ANNOUNCEMENTS = "public"
    TYPE_ALL_CATEGORIES = "all"

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
        super().__init__(*args, **kwargs)
        choices = get_categories(request)
        choices.insert(0, (self.TYPE_ALL_CATEGORIES, _("All categories")))
        self.fields["category"].choices = choices


class FilterMessageAdminForm(FilterMessageForm):
    author = UserSelectionField(label=_("Author username"), required=False)

    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["author"].hints_url = reverse("get_messages_authors", kwargs={"contest_id": request.contest.id})
        self.fields["author"].widget.attrs["placeholder"] = _("Author username")


class NewsMessageForm(PublicMessageForm):
    class Meta:
        model = NewsMessage
        fields = ["content"]


class AddQuestionMessageForm(PublicMessageForm):
    class Meta:
        model = AddQuestionMessage
        fields = ["content"]
