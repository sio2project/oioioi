from django.core.exceptions import ValidationError
from django.db import models
from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from south.modelsinspector import add_introspection_rules
import re


class ColorWidget(forms.TextInput):
    """Based on:
       http://laktek.com/2008/10/27/really-simple-color-picker-in-jquery/
       Requires jQuery > 1.2.6

       Displays a fixed set of preselected color options.
       Hex value can also be edited manually.
       Only supports Hex values.  Alpha channel not supported.
    """
    class Media(object):
        js = ('js/jquery.colorPicker.js',)

    def render(self, name, value, attrs=None):
        rendered = super(ColorWidget, self).render(name, value, attrs)
        return rendered + mark_safe(u'''<script type="text/javascript">
            $('#id_%s').colorPicker();
            </script>''' % name)


class ColorField(models.CharField):
    _re = re.compile('^#[0-9a-f]{6}$')

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 7
        super(ColorField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['widget'] = ColorWidget
        return super(ColorField, self).formfield(**kwargs)

    def to_python(self, value):
        value = unicode(value).lower()
        if self._re.match(value) is None:
            raise ValidationError(_("Value '%s' is not a valid color, "
                "expected something like #aa34bc."))
        return value

add_introspection_rules([], [r'^oioioi\.base\.utils\.color\.ColorField'])
