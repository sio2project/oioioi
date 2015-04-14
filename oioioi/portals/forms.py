from django.forms import ModelForm
from oioioi.portals.models import Node


class NodeForm(ModelForm):
    class Meta(object):
        model = Node
        fields = ('full_name', 'short_name', 'panel_code')

    def __init__(self, *args, **kwargs):
        super(NodeForm, self).__init__(*args, **kwargs)

        instance = kwargs.pop('instance', None)
        if instance is not None and instance.parent is None:
            del self.fields['short_name']
