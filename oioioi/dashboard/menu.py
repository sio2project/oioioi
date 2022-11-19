from django.utils.translation import gettext_lazy as _

from oioioi.base.menu import MenuRegistry
from oioioi.base.permissions import not_anonymous
from oioioi.contests.utils import contest_exists

top_links_registry = MenuRegistry(_("Top Links Menu"), contest_exists & not_anonymous)
