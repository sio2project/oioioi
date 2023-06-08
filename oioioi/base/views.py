import traceback
from django.conf import settings

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import LogoutView as AuthLogoutView
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.vary import vary_on_cookie, vary_on_headers
from two_factor.views import LoginView as Login2FAView

import oioioi.base.forms
from oioioi.base.forms import handle_new_preference_fields
from oioioi.base.menu import account_menu_registry
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.base.preferences import PreferencesFactory, ensure_preferences_exist_for_user
from oioioi.base.processors import site_name
from oioioi.base.utils import generate_key, is_ajax, jsonify
from oioioi.base.utils.redirect import safe_redirect
from oioioi.base.utils.user import has_valid_username

account_menu_registry.register(
    'change_password',
    _("Change password"),
    lambda request: reverse('auth_password_change'),
    order=100,
)
account_menu_registry.register(
    'two_factor_auth',
    _("Two factor authentication"),
    lambda request: reverse('two_factor:profile'),
    order=150,
)


class ForcedError(Exception):
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
        if is_ajax(request):
            return plain_resp
        return render(request, '500.html', {'traceback': tb}, status=500)
    except Exception:
        return plain_resp


def handler404(request, exception):
    if is_ajax(request):
        return HttpResponse('404 Not Found', status=404, content_type='text/plain')
    # DO NOT USE django.views.defaults.page_not_found here
    # It has a known vulnaribility before 1.11.18
    # DO NOT DISPLAY request.path without using urllib.parse.quote() first
    # See:
    # https://security.archlinux.org/AVG-838
    # https://www.djangoproject.com/weblog/2019/jan/04/security-releases/
    # https://github.com/django/django/commit/64d2396e83aedba3fcc84ca40f23fbd22f0b9b5b
    # https://github.com/django/django/commit/1cd00fcf52d089ef0fe03beabd05d59df8ea052a
    return render(request, '404.html', status=404)


def handler403(request, exception):
    if is_ajax(request):
        return HttpResponse('403 Forbidden', status=403, content_type='text/plain')
    message = render_to_string('403.html', request=request)
    return HttpResponseForbidden(message)


@account_menu_registry.register_decorator(
    _("Edit profile"), lambda request: reverse('edit_profile'), order=99
)
@enforce_condition(not_anonymous)
def edit_profile_view(request):
    ensure_preferences_exist_for_user(request.user)
    if request.method == 'POST':
        form = PreferencesFactory().create_form(
            oioioi.base.forms.UserChangeForm,
            request.user,
            request.POST,
            allow_login_change=not has_valid_username(request.user),
        )

        handle_new_preference_fields(request, request.user)

        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = PreferencesFactory().create_form(
            oioioi.base.forms.UserChangeForm,
            request.user,
            allow_login_change=not has_valid_username(request.user),
        )
    return TemplateResponse(
        request, 'registration/registration_form.html', {'form': form}
    )


@account_menu_registry.register_decorator(
    _("Log out"),
    lambda request: '#',
    order=200,
    attrs={'data-post-url': reverse_lazy('logout')},
)
@require_POST
def logout_view(request):
    return AuthLogoutView.as_view()(
        request,
        template_name='registration/logout.html',
        extra_context=site_name(request),
    )


def login_view(request, redirect_field_name=REDIRECT_FIELD_NAME, **kwargs):
    if request.user.is_authenticated:
        redirect_to = request.GET.get(redirect_field_name, None)
        return safe_redirect(request, redirect_to)
    else:
        return Login2FAView.as_view(**kwargs)(request)


@require_GET
@vary_on_headers('Content-Language')
@vary_on_cookie
@cache_control(public=True, max_age=900)
@jsonify
def translate_view(request):
    if 'query' in request.GET:
        return {'answer': gettext(request.GET['query'])}
    else:
        raise SuspiciousOperation


def delete_account_view(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    failed_password = False
    if request.POST:
        auth_password = request.POST['auth-password']
        if request.user.check_password(auth_password):
            for participant in request.user.participant_set.all():
                participant.erase_data()
            request.user.is_active = False
            request.user.save()
            return AuthLogoutView.as_view()(
                request, template_name='registration/delete_account_done.html'
            )
        else:
            failed_password = True

    return TemplateResponse(
        request,
        'registration/delete_account_confirmation.html',
        context={'failed': failed_password},
    )


def generate_key_view(request):
    return HttpResponse(generate_key())
