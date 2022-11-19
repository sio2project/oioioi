import re

import django
from django import forms
from django.core.validators import RegexValidator
from django.db import models
from django.utils.safestring import mark_safe


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

    def render(self, name, value, attrs=None, renderer=None):
        html = super(ColorWidget, self).render(name, value, attrs, renderer)
        return html + mark_safe(
            u'''<script type="text/javascript">
            $('#id_%s').colorPicker();
            </script>'''
            % name
        )


class ColorField(models.CharField):
    _re = re.compile('^#[0-9a-f]{6}$')
    default_validators = [RegexValidator(_re, 'Invalid color value.')]

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 7
        super(ColorField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['widget'] = ColorWidget
        return super(ColorField, self).formfield(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(ColorField, self).deconstruct()
        del kwargs['max_length']
        return name, path, args, kwargs
