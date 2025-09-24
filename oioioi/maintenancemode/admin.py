from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.admin import system_admin_menu_registry

system_admin_menu_registry.register(
    "maintenance_mode",
    _("Maintenance mode"),
    lambda request: reverse("set_maintenance_mode"),
    order=60,
)
