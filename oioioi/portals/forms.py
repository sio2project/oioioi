from django.conf import settings
from django.forms import (
    CharField,
    ChoiceField,
    Form,
    HiddenInput,
    ModelForm,
    TextInput,
    ValidationError,
    inlineformset_factory,
)
from django.utils.translation import gettext_lazy as _

from oioioi.portals.models import Node, NodeLanguageVersion, Portal


class NodeForm(ModelForm):
    class Meta:
        model = Node
        fields = ("short_name",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = kwargs.pop("instance", None)
        if instance is not None and instance.parent is None:
            del self.fields["short_name"]

    def clean_short_name(self):
        short_name = self.cleaned_data["short_name"]

        if self.instance.parent is None:
            return short_name

        same = self.instance.parent.children.filter(short_name=short_name)
        if same.exists() and same.get() != self.instance:
            raise ValidationError(
                _("Node %(parent)s already has a child with this short name."),
                params={"parent": self.instance.parent.get_lang_version().full_name},
            )

        return short_name


class NodeLanguageVersionForm(ModelForm):
    class Meta:
        model = NodeLanguageVersion
        fields = (
            "language",
            "full_name",
            "panel_code",
        )

    language = ChoiceField(widget=HiddenInput(), choices=settings.LANGUAGES)


NodeLanguageVersionFormset = inlineformset_factory(
    Node,
    NodeLanguageVersion,
    form=NodeLanguageVersionForm,
    extra=len(settings.LANGUAGES),
    min_num=1,
    max_num=len(settings.LANGUAGES),
    validate_min=True,
    validate_max=True,
    can_delete=True,
)


class PortalsSearchForm(Form):
    q = CharField(
        max_length=30,
        label=None,
        widget=TextInput(
            attrs={
                "placeholder": _("Search by URL or name"),
                "class": "form-control search-query",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.query = kwargs.pop("query")
        super().__init__(*args, **kwargs)
        self.fields["q"].initial = self.query


class PortalShortDescForm(ModelForm):
    class Meta:
        model = Portal
        fields = ("short_description",)


class PortalInfoForm(ModelForm):
    class Meta:
        model = Portal
        fields = ("short_description", "is_public")


class LinkNameForm(ModelForm):
    class Meta:
        model = Portal
        fields = ("link_name",)
