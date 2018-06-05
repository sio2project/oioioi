from django.conf import settings
from django.core.urlresolvers import get_script_prefix

from oioioi.base.menu import side_pane_menus_registry


def base_url(request):
    return {'base_url': get_script_prefix()}


def side_menus(request):
    menus = [m for m in side_pane_menus_registry if m.condition(request)]
    return {'side_menus': menus}


def site_name(request):
    return {'site_name': settings.SITE_NAME}


def mathjax_location(request):
    return {'mathjax_location': settings.MATHJAX_LOCATION}
