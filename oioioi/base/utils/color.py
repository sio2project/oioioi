import re

import django
from django import forms
from django.core.validators import RegexValidator
from django.db import models
from django.utils.safestring import mark_safe


class ColorWidget(forms.TextInput):
    input_type = "color"


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
