from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from oioioi.base.permissions import enforce_condition
from oioioi.base.menu import menu_registry
from oioioi.base.utils.execute import execute, ExecuteError
from oioioi.contests.utils import can_enter_contest
from oioioi.printing.pdf import generator, PageLimitExceeded

menu_registry.register('print_view', _("Print file"),
        lambda request: reverse('print_view', kwargs={'contest_id':
        request.contest.id}), order=470)

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
        return scleaned_data

@enforce_condition(can_enter_contest)
def print_view(request, contest_id):
    error_message = None
    success_message = None
    if request.method == 'POST':
        form = PrintForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            try:
                execute(['lp'], stdin=form.cleaned_data['file'])
            except ExecuteError as e:
                error_message = unicode(e)
            else:
                success_message = _("File has been printed.")

    else:
        form = PrintForm(request.user)

    return TemplateResponse(request, 'printing/print.html',
                    {'form': form, 'success_message': success_message,
                     'error_message': error_message})
