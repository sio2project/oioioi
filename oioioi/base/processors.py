from django.conf import settings
from django.urls import get_script_prefix
from django.utils.functional import lazy
from django.utils.module_loading import import_string
from django_gravatar.helpers import get_gravatar_url

from oioioi.base.menu import side_pane_menus_registry


def base_url(request):
    return {'base_url': get_script_prefix()}


def side_menus(request):
    menus = [m for m in side_pane_menus_registry if m.condition(request)]
    nonempty_menus = []

    for menu in menus:
        if isinstance(menu, str):
            menu = import_string(menu)

        if menu.is_anything_accessible(request):
            nonempty_menus.append(menu)

    return {'side_menus': nonempty_menus}


def site_name(request):
    return {'site_name': settings.SITE_NAME}


def mathjax_location(request):
    return {'mathjax_location': settings.MATHJAX_LOCATION}


def compress_offline(request):
    return {'compress_offline': settings.COMPRESS_OFFLINE}


def gravatar(request):
    if request.user.is_authenticated:

        def generator():
            return str(get_gravatar_url(request.user.email or 'oioioi', size=25))

        return {'avatar': lazy(generator, str)()}
    else:
        return {}
