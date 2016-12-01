from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response, redirect, render
from django.http import HttpResponse, HttpResponseForbidden
from django.template import TemplateDoesNotExist, RequestContext
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.views.defaults import page_not_found
from django.utils.translation import ugettext, ugettext_lazy as _
from django.views.decorators.http import require_POST, require_GET
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.auth.views import logout as auth_logout, \
                                      login as auth_login
from django.views.decorators.vary import vary_on_headers, vary_on_cookie
from django.views.decorators.cache import cache_control
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.base.utils.redirect import safe_redirect
from oioioi.base.utils.user import has_valid_username
from oioioi.contests.models import Contest
from oioioi.base.forms import UserForm
from oioioi.base.utils import jsonify, generate_key
from oioioi.base.menu import account_menu_registry
from oioioi.base.preferences import PreferencesFactory
from oioioi.base.processors import site_name
import traceback

account_menu_registry.register('change_password', _("Change password"),
        lambda request: reverse('auth_password_change'), order=100)


class ForcedError(StandardError):
    pass


def force_error_view(request):
    raise ForcedError("Visited /force_error")


def force_permission_denied_view(request):
    raise PermissionDenied("Visited /force_permission_denied")


def handler500(request):
    # pylint: disable=broad-except
    message = '500 Internal Server Error'

    tb = ''
    try:
        tb = traceback.format_exc()
        if hasattr(request, 'user') and request.user.is_superuser:
            message += '\n' + tb
    except Exception:
        pass

    plain_resp = HttpResponse(message, status=500, content_type='text/plain')

    try:
        if request.is_ajax():
            return plain_resp
        return render(request, '500.html', {'traceback': tb}, status=500)
    except Exception:
        return plain_resp


def handler404(request):
    if request.is_ajax():
        return HttpResponse('404 Not Found', status=404,
                            content_type='text/plain')
    return page_not_found(request)


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
        form = PreferencesFactory().create_form(
            request.user,
            request.POST,
            allow_login_change=not has_valid_username(request.user)
        )
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = PreferencesFactory().create_form(
            request.user,
            allow_login_change=not has_valid_username(request.user)
        )
    return TemplateResponse(request, 'registration/registration_form.html',
            {'form': form})


@account_menu_registry.register_decorator(_("Log out"), lambda request: '#',
    order=200, attrs={'data-post-url': reverse_lazy('logout')})
@require_POST
def logout_view(request):
    return auth_logout(request, template_name='registration/logout.html',
            extra_context=site_name(request))


def login_view(request, redirect_field_name=REDIRECT_FIELD_NAME, **kwargs):
    if request.user.is_authenticated():
        redirect_to = request.REQUEST.get(redirect_field_name, None)
        return safe_redirect(request, redirect_to)
    else:
        return auth_login(request, extra_context=site_name(request), **kwargs)


@require_GET
@vary_on_headers('Content-Language')
@vary_on_cookie
@cache_control(public=True, max_age=900)
@jsonify
def translate_view(request):
    if 'query' in request.GET:
        return {'answer': ugettext(request.GET['query'])}
    else:
        raise SuspiciousOperation


def delete_account_view(request):
    if not request.user.is_authenticated():
        return HttpResponseForbidden()

    if request.POST:
        for participant in request.user.participant_set.all():
            participant.erase_data()
        request.user.is_active = False
        request.user.save()
        return auth_logout(request,
                template_name='registration/delete_account_done.html')

    return TemplateResponse(request,
            'registration/delete_account_confirmation.html')


def generate_key_view(request):
    return HttpResponse(generate_key())
