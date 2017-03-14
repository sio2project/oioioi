# pylint: disable=no-name-in-module, line-too-long
from django.forms.utils import flatatt
from django.template.loader import render_to_string
from django import forms


class DateTimePicker(forms.widgets.DateTimeInput):
    class Media(object):
        js = ['bootstrap-datetimepicker-oioioi/moment.min.js',
              'bootstrap-datetimepicker-oioioi/pl.js',
              'bootstrap-datetimepicker-oioioi/bootstrap-datetimepicker.min.js']
        css = {'all': ('bootstrap-datetimepicker-oioioi/bootstrap-datetimepicker.min.css',)}

    def __init__(self, *args, **kwargs):
        super(DateTimePicker, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        return render_to_string('widgets/datetimepicker.html',
                {'name': name, 'value': value,
                 'attrs': flatatt(self.build_attrs(attrs))})
