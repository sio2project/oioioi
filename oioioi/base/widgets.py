# pylint: disable=no-name-in-module, line-too-long
from django import forms
from django.forms.utils import flatatt
from django.template.loader import render_to_string


# passing classes through the usual attrs attribute won't work
# since the template already specifies it
class DateTimePicker(forms.widgets.DateTimeInput):
    class Media(object):
        js = [
            'tempus-dominus/pl.js',
            'tempus-dominus/tempus-dominus.min.js',
            'tempus-dominus/jQuery-provider.min.js',
        ]
        css = {
            'all': ('tempus-dominus/tempus-dominus.min.css',)
        }

    def __init__(self, *args, **kwargs):
        super(DateTimePicker, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        return render_to_string(
            'widgets/datetimepicker.html',
            {'name': name, 'value': value, 'attrs': flatatt(self.build_attrs(attrs))},
        )

class AceEditorWidget(forms.widgets.Textarea):
    def __init__(self, attrs, default_state=False):
        super(AceEditorWidget, self).__init__(attrs={'rows': 10, 'class': 'monospace'})
        self.default_state = default_state

    def render(self, name, value, attrs=None, renderer=None):
        return super(AceEditorWidget, self).render(name, value, attrs=attrs, renderer=renderer) + \
            render_to_string('widgets/aceeditor.html',
             {'editor_id': 'editor',
             'inner_code': '',
             'replace_code_area': 'textarea[name="code"]',
             'toggle_checkbox_id': 'id_toggle_editor',
             'default_state': 'true' if self.default_state else 'false'},)