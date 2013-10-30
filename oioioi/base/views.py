from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import render_to_response, redirect, render
from django.http import HttpResponse, HttpResponseForbidden
from django.template import TemplateDoesNotExist, RequestContext
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.auth.views import logout as auth_logout, \
                                      login as auth_login
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.views import default_contest_view
from oioioi.base.forms import UserForm
from oioioi.base.menu import account_menu_registry
import traceback

account_menu_registry.register('change_password', _("Change password"),
        lambda request: reverse('auth_password_change'), order=100)


def index_view(request):
    try:
        return render_to_response("index.html",
                context_instance=RequestContext(request))
    except TemplateDoesNotExist:
        if not request.contest:
            return TemplateResponse(request, "index-no-contests.html")
        return default_contest_view(request, request.contest.id)


def force_error_view(request):
    raise StandardError("Visited /force_error")


def handler500(request):
    tb = ''
    try:
        tb = traceback.format_exc()
        return render(request, '500.html', {'traceback': tb}, status=500)
    except Exception:
        message = '500 Internal Server Error'
        if hasattr(request, 'user') and request.user.is_superuser:
            message += '\n' + tb
        return HttpResponse(message, status=500, content_type='text/plain')


def handler403(request):
    if request.is_ajax():
        return HttpResponse('403 Forbidden', status=403,
                content_type='text/plain')
    message = render_to_string('403.html',
            context_instance=RequestContext(request))
    return HttpResponseForbidden(message)


@account_menu_registry.register_decorator(_("Edit profile"),
    lambda request: reverse('edit_profile'), order=99)
@enforce_condition(not_anonymous)
def edit_profile_view(request):
    if request.method == 'POST':
        form = UserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect(index_view)
    else:
        form = UserForm(instance=request.user)
    return TemplateResponse(request, 'registration/registration_form.html',
            {'form': form})


@account_menu_registry.register_decorator(_("Log out"), lambda request: '#',
    order=200, attrs={'data-post-url': reverse_lazy('logout')})
@require_POST
def logout_view(request):
    return auth_logout(request, template_name='registration/logout.html')


def login_view(request, redirect_field_name=REDIRECT_FIELD_NAME, **kwargs):
    if request.user.is_authenticated():
        redirect_to = request.REQUEST.get(redirect_field_name, None)
        return safe_redirect(request, redirect_to)
    else:
        return auth_login(request, **kwargs)
