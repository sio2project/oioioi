from django.utils.translation import ugettext_lazy as _

from oioioi.base.menu import MenuRegistry, side_pane_menus_registry
from oioioi.contests.utils import is_contest_admin

contest_admin_menu_registry = MenuRegistry(_("Contest Administration"),
    lambda request: hasattr(request, 'contest') and is_contest_admin(request))
side_pane_menus_registry.register(contest_admin_menu_registry, order=100)
