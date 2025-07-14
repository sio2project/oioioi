from datetime import timedelta  # pylint: disable=E0611

from django.conf import settings
from django.contrib.admin.utils import quote
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from oioioi.balloons.models import (
    BalloonDelivery,
    BalloonsDeliveryAccessData,
    BalloonsDisplay,
    ProblemBalloonsConfig,
)
from oioioi.base.permissions import enforce_condition, make_request_condition
from oioioi.base.utils import jsonify
from oioioi.contests.models import Contest, UserResultForProblem
from oioioi.contests.utils import can_enter_contest, contest_exists, is_contest_admin


@make_request_condition
def has_balloons_cookie(request):
    try:
        key = request.COOKIES["balloons_access_%s" % request.contest.id]
        access_data = BalloonsDeliveryAccessData.objects.get(contest__id=request.contest.id, access_key=key)
    except (KeyError, BalloonsDeliveryAccessData.DoesNotExist):
        return False
    if access_data.valid_until < request.timestamp:
        return False
    return True


def balloons_context(user, list_of_colors):
    if len(list_of_colors) <= 1:
        step = 0
    else:
        step = 60 / (len(list_of_colors) - 1)
    balloons = [
        {
            "color": c[1:],
            "left": 20 + i * step,
        }
        for i, c in enumerate(list_of_colors)
    ]
    return {"balloons_user": user, "balloons": balloons}


def query_context_args(user, contest):
    return (
        UserResultForProblem.objects.filter(
            problem_instance__contest=contest,
            user=user,
            status="OK",
            problem_instance__balloons_config__color__isnull=False,
        )
        .order_by("submission_report__submission__date")
        .values_list("problem_instance__balloons_config__color", flat=True)
    )


def context_args(request):
    if request.user.is_authenticated and can_enter_contest(request) and request.contest is not None:
        return request.user, query_context_args(request.user, request.contest)
    ip_addr = request.META.get("REMOTE_ADDR")
    if not ip_addr:
        raise Http404(_("No IP address detected"))
    try:
        display = BalloonsDisplay.objects.get(ip_addr=ip_addr)
    except BalloonsDisplay.DoesNotExist:
        raise Http404(_("No balloons display configured for this IP: %s") % (ip_addr,))
    return display.user, query_context_args(display.user, display.contest)


def balloon_svg_view(request, color):
    return TemplateResponse(
        request,
        "balloons/balloon.svg",
        {"color": "#" + color},
        content_type="image/svg+xml",
    )


def balloons_view(request):
    args = context_args(request)
    return TemplateResponse(request, "balloons/balloons.html", balloons_context(*args))


def balloons_body_view(request):
    args = context_args(request)
    return TemplateResponse(request, "balloons/balloons-body.html", balloons_context(*args))


@enforce_condition(contest_exists & is_contest_admin)
@require_POST
def balloons_regenerate_delivery_key_view(request):
    contest = get_object_or_404(Contest, id=request.contest.id)
    access_data = BalloonsDeliveryAccessData.objects.get_or_create(contest=contest)[0]
    access_data.valid_until = None
    access_data.generate_key()
    access_data.save()

    return redirect("oioioiadmin:contests_contest_change", quote(request.contest.id))


def balloons_access_cookie_view(request, access_key):
    access_data = get_object_or_404(BalloonsDeliveryAccessData, contest_id=request.contest.id, access_key=access_key)
    if access_data.valid_until is not None:
        raise PermissionDenied
    expires = settings.BALLOON_ACCESS_COOKIE_EXPIRES_DAYS
    validity_date = request.timestamp + timedelta(days=expires)
    access_data.valid_until = validity_date
    access_data.save()
    response = redirect("balloons_delivery_panel", contest_id=request.contest.id)
    response.set_cookie(
        key="balloons_access_%s" % request.contest.id,
        value=access_key,
        expires=validity_date,
    )
    return response


@enforce_condition(has_balloons_cookie, login_redirect=False)
def balloons_delivery_panel_view(request):
    return TemplateResponse(request, "balloons/balloons-delivery-panel.html")


@jsonify
@enforce_condition(has_balloons_cookie, login_redirect=False)
def get_new_balloon_requests_view(request):
    try:
        last_id = int(request.GET["last_id"])
    except KeyError:
        raise Http404
    new_requests = BalloonDelivery.objects.filter(id__gt=last_id, problem_instance__contest_id=request.contest.id, delivered=False).select_related(
        "user", "problem_instance__balloons_config"
    )[:10]
    response = {"new_last_id": last_id, "new_requests": []}
    if not new_requests:
        return response
    response["new_last_id"] = max(r.id for r in new_requests)
    for delivery in new_requests:
        try:
            balloon_config = delivery.problem_instance.balloons_config
            color = balloon_config.color
        except ProblemBalloonsConfig.DoesNotExist:
            color = None
        response["new_requests"].append(
            {
                "id": delivery.id,
                "team": delivery.user.get_full_name(),
                "color": color,
                "problem_name": delivery.problem_instance.short_name,
                "first_accepted": delivery.first_accepted_solution,
            }
        )
    return response


@jsonify
@enforce_condition(has_balloons_cookie, login_redirect=False)
@require_POST
def set_balloon_delivered_view(request):
    try:
        new_delivered = request.POST["new_delivered"] == "True"
        old_delivered = not new_delivered
        delivery = BalloonDelivery.objects.get(id=int(request.POST["id"]), delivered=old_delivered)
    except (KeyError, BalloonDelivery.DoesNotExist):
        raise Http404
    delivery.delivered = new_delivered
    delivery.save()
    return {"result": "ok"}
