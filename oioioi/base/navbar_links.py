from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.menu import navbar_links_registry
from oioioi.contests.current_contest import ContestMode, reverse


if settings.CONTEST_MODE == ContestMode.neutral:
    navbar_links_registry.register(
        name='contests_list',
        text=_("Contests"),
        url_generator=lambda request: reverse('select_contest'),
        order=100,
    )

navbar_links_registry.register(
    name='problemset',
    text=_("Problemset"),
    url_generator=lambda request: reverse('problemset_main'),
    order=200,
)

navbar_links_registry.register(
    name='task_archive',
    text=_("Task archive"),
    url_generator=lambda request: reverse('task_archive'),
    order=300,
)
