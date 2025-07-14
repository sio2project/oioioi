from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.utils import is_contest_admin

contest_admin_menu_registry.register(
    "plagiarism",
    _("Plagiarism tools"),
    lambda request: reverse("moss_submit"),
    is_contest_admin,
    order=100,
)
