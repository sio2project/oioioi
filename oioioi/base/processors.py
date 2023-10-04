from django.conf import settings
from django.urls import get_script_prefix
from django.utils import timezone
from django.utils.functional import lazy
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from django_gravatar.helpers import get_gravatar_url

from oioioi.base.menu import side_pane_menus_registry, MenuRegistry
from oioioi.base.navbar_links import navbar_links_registry
from oioioi.contests.models import Round


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


def navbar_links(request):
    current_time = timezone.now()

    if hasattr(request, 'contest'):
        running_rounds = Round.objects.filter(contest=request.contest, start_date__lte=current_time,
                                              end_date__gt=current_time)

        if running_rounds.exists():
            empty_navbar_links_registry = MenuRegistry(_("Navigation Bar Menu"))
            no_links = empty_navbar_links_registry.template_context(request)

            return {'navbar_links': no_links}

    links = navbar_links_registry.template_context(request)

    return {'navbar_links': links}


def site_name(request):
    return {'site_name': settings.SITE_NAME}


def mathjax_location(request):
    return {'mathjax_location': settings.MATHJAX_LOCATION}


def gravatar(request):
    if request.user.is_authenticated:

        def generator():
            return str(get_gravatar_url(request.user.email or 'oioioi', size=25))

        return {'avatar': lazy(generator, str)()}
    else:
        return {}
