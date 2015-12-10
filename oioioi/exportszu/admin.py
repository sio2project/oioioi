from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.menu import contest_admin_menu_registry

contest_admin_menu_registry.register('export_submissions',
    _("Export submissions"),
    lambda request: reverse('export_submissions'), order=100)
