from django.forms import ModelForm, ValidationError, Form, CharField, TextInput
from django.utils.translation import ugettext_lazy as _

from oioioi.portals.models import Node, Portal


class NodeForm(ModelForm):
    class Meta(object):
        model = Node
        fields = ('full_name', 'short_name', 'panel_code')

    def __init__(self, *args, **kwargs):
        super(NodeForm, self).__init__(*args, **kwargs)

        instance = kwargs.pop('instance', None)
        if instance is not None and instance.parent is None:
            del self.fields['short_name']

    def clean_short_name(self):
        short_name = self.cleaned_data['short_name']

        if self.instance.parent is None:
            return short_name

        same = self.instance.parent.children.filter(short_name=short_name)
        if same.exists() and same.get() != self.instance:
            raise ValidationError(_("Node %(parent)s already has a child " +
                                    "with this short name."),
                    params={'parent': self.instance.parent.full_name})

        return short_name


class PortalsSearchForm(Form):
    q = CharField(max_length=30, label=None,
                  widget=TextInput(attrs={'placeholder':
                                              _('Search by URL or name'),
                                          'class':
                                              "form-control search-query"}))

    def __init__(self, *args, **kwargs):
        self.query = kwargs.pop('query')
        super(PortalsSearchForm, self).__init__(*args, **kwargs)
        self.fields['q'].initial = self.query


class PortalShortDescForm(ModelForm):
    class Meta(object):
        model = Portal
        fields = ('short_description',)


class PortalInfoForm(ModelForm):
    class Meta(object):
        model = Portal
        fields = ('short_description', 'is_public')


class LinkNameForm(ModelForm):
    class Meta(object):
        model = Portal
        fields = ('link_name',)
