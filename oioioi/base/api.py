from django.template.response import TemplateResponse
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from oioioi.base.menu import account_menu_registry
from oioioi.base.permissions import (enforce_condition, not_anonymous)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authtoken.models import Token


@api_view()
def ping(request):
    """ Test endpoint for unauthorized user. """
    return Response("pong")


@api_view()
@enforce_condition(not_anonymous, login_redirect=False)
def auth_ping(request):
    """ Test endpoint for authorized user. """
    return Response("pong " + str(request.user))


def api_token(request, regenerated=False):
    if request.method != 'POST':
        return TemplateResponse(request, 'api-key.html', {})
    token, created = Token.objects.get_or_create(user=request.user)
    return TemplateResponse(request, 'api-key.html',
                            {"token": token, "regenerated": regenerated})


def regenerate_token(request):
    if request.method != 'POST':
        return api_token(request)
    Token.objects.filter(user=request.user).delete()
    return api_token(request, regenerated=True)


def api_token_url(request):
    return reverse('api_token')


if settings.USE_API:
    account_menu_registry.register('api_token', _('Your API token'), api_token_url, order=160)
