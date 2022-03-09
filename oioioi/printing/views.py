import six
from django.conf import settings
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import (
    enforce_condition,
    make_request_condition,
    not_anonymous,
)
from oioioi.base.utils.execute import ExecuteError, execute
from oioioi.contests.utils import contest_exists, has_any_submittable_problem
from oioioi.printing.forms import PrintForm


@make_request_condition
def can_print_files(request):
    return request.contest.controller.can_print_files(request)


@menu_registry.register_decorator(
    _("Print file"),
    lambda request: reverse('print_view', kwargs={'contest_id': request.contest.id}),
    order=470,
)
@enforce_condition(not_anonymous & contest_exists)
@enforce_condition(can_print_files)
@enforce_condition(
    has_any_submittable_problem, template='printing/nothing_to_print.html'
)
def print_view(request):
    error_message = None
    success_message = None

    if request.method == 'POST':
        form = PrintForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            try:
                execute(settings.PRINTING_COMMAND, stdin=form.cleaned_data['file'])
            except ExecuteError as e:
                error_message = six.text_type(e)
            else:
                success_message = _("File has been printed.")

    else:
        form = PrintForm(request.user)

    return TemplateResponse(
        request,
        'printing/print.html',
        {
            'form': form,
            'success_message': success_message,
            'error_message': error_message,
        },
    )
