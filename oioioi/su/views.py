from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from oioioi.base.permissions import enforce_condition, is_superuser
from oioioi.base.utils.redirect import safe_redirect
from oioioi.base.utils.user_selection import get_user_hints_view
from oioioi.contests.models import ContestPermission
from oioioi.contests.utils import is_contest_basicadmin, contest_exists, can_admin_contest
from oioioi.participants.models import Participant
from oioioi.status.registry import status_registry
from oioioi.su.forms import SuForm
from oioioi.su.middleware import REDIRECTION_AFTER_SU_KEY
from oioioi.su.utils import (
    is_real_superuser,
    is_under_su,
    reset_to_real_user,
    su_to_user,
    can_contest_admins_su,
)


@enforce_condition(is_superuser | (can_contest_admins_su & contest_exists & is_contest_basicadmin))
@require_POST
def su_view(request, next_page=None, redirect_field_name=REDIRECT_FIELD_NAME):
    form = SuForm(request.POST)
    if not form.is_valid():
        return TemplateResponse(
            request,
            'simple-centered-form.html',
            {
                'form': form,
                'action': reverse('su'),
                'title': _("Login as another user"),
            },
        )

    user = form.cleaned_data['user']
    if is_under_su(request):
        raise SuspiciousOperation

    # Don't allow contest admins to switch to users that are not participants of the contest
    if (
        not is_superuser(request) and
        request.contest.controller.registration_controller().filter_users_with_accessible_personal_data(
            User.objects.filter(id=user.id)
        ).count() == 0
    ):
        raise SuspiciousOperation

    # Don't allow contest admins to switch to other contest admins
    if not is_superuser(request) and can_admin_contest(user, request.contest):
        raise SuspiciousOperation

    # Don't allow real superusers switched to contest admins to switch to other contest admins
    if is_real_superuser(request) and can_admin_contest(user, request.contest):
        raise SuspiciousOperation

    su_to_user(request, user, form.cleaned_data['backend'])

    if redirect_field_name in request.GET:
        next_page = request.GET[redirect_field_name]
    elif redirect_field_name in request.POST:
        next_page = request.POST[redirect_field_name]

    request.session[REDIRECTION_AFTER_SU_KEY] = 'PRE_SU'

    return safe_redirect(request, next_page)


@enforce_condition(is_under_su)
@require_POST
def su_reset_view(request, next_page=None, redirect_field_name=REDIRECT_FIELD_NAME):
    reset_to_real_user(request)
    if redirect_field_name in request.GET:
        next_page = request.GET[redirect_field_name]
    elif redirect_field_name in request.POST:
        next_page = request.POST[redirect_field_name]

    return safe_redirect(request, next_page)


@enforce_condition(is_superuser | (can_contest_admins_su & contest_exists & is_contest_basicadmin))
def get_suable_users_view(request):
    if not is_superuser(request):
        cps = ContestPermission.objects.filter(
            contest=request.contest,
            permission__in=[
                "contests.contest_owner",
                "contests.contest_admin",
                "contests.contest_basicadmin",
            ]
        ).select_related("user")
        contest_admins = [cp.user.id for cp in cps]

        users = request.contest.controller.registration_controller().filter_users_with_accessible_personal_data(
            User.objects.filter(
                is_active=True,
                is_superuser=False,
            ).exclude(id__in=contest_admins)
        )
    else:
        users = User.objects.filter(is_superuser=False, is_active=True)
    return get_user_hints_view(request, 'substr', users)


@status_registry.register
def get_su_status(request, response):
    response['is_real_superuser'] = is_real_superuser(request)
    response['is_under_su'] = is_under_su(request)
    response['real_user'] = request.real_user.username
    if is_real_superuser(request):
        response['sync_time'] = min(10000, response.get('sync_time', 10000))

    return response


def method_not_allowed_view(request):
    return TemplateResponse(request, 'su/method-not-allowed.html')


def url_not_allowed_view(request):
    return TemplateResponse(request, 'su/url-not-allowed.html')
