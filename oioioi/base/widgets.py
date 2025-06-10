# pylint: disable=no-name-in-module, line-too-long
from django import forms
from django.forms.utils import flatatt
from django.template.loader import render_to_string


# passing classes through the usual attrs attribute won't work
# since the template already specifies it
class DateTimePicker(forms.widgets.DateTimeInput):
    template_name = 'widgets/datetimepicker.html'
    
    class Media(object):
        js = ['datetimepicker.bundle.js']
        css = {
            'all': ('@eonasdan/tempus-dominus/dist/css/tempus-dominus.min.css',)
        }
    
    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format='%Y-%m-%d %H:%M')
        
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        
        # Don't add other classes to the input element
        context["widget"]["attrs"]["class"] = "form-control"

        return context

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
