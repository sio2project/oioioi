from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from oioioi.printing.pdf import generator, PageLimitExceeded


def is_text_file_validator(file):
    if not file.content_type.startswith('text/'):
        raise ValidationError(_("The file should be a text file."))


def validate_file_size(file):
    if file.size > settings.PRINTING_MAX_FILE_SIZE:
        raise ValidationError(_("The file size limit exceeded."))


class PrintForm(forms.Form):
    file = forms.FileField(allow_empty_file=False, label=_("File"),
                           validators=[is_text_file_validator,
                                       validate_file_size])

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(PrintForm, self).__init__(*args, **kwargs)

    def clean_file(self):
        cleaned_data = self.cleaned_data
        try:
            cleaned_data['file'] = generator(
                source=cleaned_data['file'].file.read(),
                header=unicode(self.user))
        except PageLimitExceeded:
            raise ValidationError(_("The page limit exceeded."))
        return cleaned_data['file']
