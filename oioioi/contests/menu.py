from django.utils.translation import ugettext_lazy as _

from oioioi.base.menu import MenuRegistry, side_pane_menus_registry
from oioioi.contests.utils import (can_see_personal_data, contest_exists,
                                   is_contest_admin, is_contest_observer)

contest_admin_menu_registry = MenuRegistry(_("Contest Administration"),
    contest_exists & is_contest_admin)
side_pane_menus_registry.register(contest_admin_menu_registry, order=100)

contest_observer_menu_registry = MenuRegistry(_("Observer Menu"),
    contest_exists & is_contest_observer & (~is_contest_admin))
side_pane_menus_registry.register(contest_observer_menu_registry, order=200)

personal_data_menu_registry = MenuRegistry(_("Personal Data Menu"),
    contest_exists & can_see_personal_data)
side_pane_menus_registry.register(personal_data_menu_registry, order=300)
