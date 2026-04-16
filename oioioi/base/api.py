from django.conf import settings
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.response import Response

from oioioi.base.menu import account_menu_registry
from oioioi.base.permissions import enforce_condition, not_anonymous


@extend_schema(responses={200: OpenApiTypes.STR}, examples=[OpenApiExample(name="response", value="pong", summary="pong")])
@api_view()
def ping(request):
    """Test endpoint for unauthorized user. Returns "pong" on success."""
    return Response("pong")


@extend_schema(
    responses={
        200: OpenApiTypes.STR,
        403: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            name="Authenticated User response",
            value="pong oioioi",
            summary="Success",
            status_codes=["200"],
        ),
        OpenApiExample(
            name="Unauthenticated or forbidden",
            value={"detail": "You do not have permission to perform this action."},
            summary="Forbidden",
            status_codes=["403"],
        ),
    ],
)
@api_view()
@enforce_condition(not_anonymous, login_redirect=False)
def auth_ping(request):
    """Test endpoint for authorized user. Returns "pong" and a stringified Django user object of the authenticated user."""
    return Response("pong " + str(request.user))


@enforce_condition(not_anonymous, login_redirect=False)
def api_token(request, regenerated=False):
    if request.method != "POST":
        return TemplateResponse(request, "api-key.html", {})
    token, created = Token.objects.get_or_create(user=request.user)
    return TemplateResponse(request, "api-key.html", {"token": token, "regenerated": regenerated})


def regenerate_token(request):
    if request.method != "POST":
        return api_token(request)
    Token.objects.filter(user=request.user).delete()
    return api_token(request, regenerated=True)


def api_token_url(request):
    return reverse("api_token")


if settings.USE_API:
    account_menu_registry.register("api_token", _("Your API token"), api_token_url, order=160)
