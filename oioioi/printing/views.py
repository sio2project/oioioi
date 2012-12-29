from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from oioioi.base.permissions import enforce_condition
from oioioi.base.menu import menu_registry
from oioioi.contests.utils import has_any_submittable_problem
from oioioi.base.utils.execute import execute, ExecuteError
from oioioi.printing.forms import PrintForm

menu_registry.register('print_view', _("Print file"),
        lambda request: reverse('print_view', kwargs={'contest_id':
        request.contest.id}), condition=has_any_submittable_problem, order=470)

@enforce_condition(has_any_submittable_problem)
def print_view(request, contest_id):
    error_message = None
    success_message = None
    if request.method == 'POST':
        form = PrintForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            try:
                execute(settings.PRINTING_COMMAND,
                        stdin=form.cleaned_data['file'])
            except ExecuteError as e:
                error_message = unicode(e)
            else:
                success_message = _("File has been printed.")

    else:
        form = PrintForm(request.user)

    return TemplateResponse(request, 'printing/print.html',
                    {'form': form, 'success_message': success_message,
                     'error_message': error_message})
