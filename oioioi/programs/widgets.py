from django import forms


class CancellableFileInput(forms.widgets.ClearableFileInput):
    template_name = 'programs/cancellable_file_input.html'

    def __init__(self, attrs=None):
        self.css_classes = []
        super(CancellableFileInput, self).__init__(attrs)

    def append_attr(self, attribute, value):
        if attribute == 'class':
            self.css_classes.append(value)
            return True
        else:
            return False

    def get_context(self, name, value, attrs):
        context = super(CancellableFileInput, self).get_context(name, value, attrs)
        context['widget'].update(
            {
                'css_classes': self.css_classes,
            }
        )
        return context

    class Media(object):
        js = ('common/cancellable_file_input.js',)
