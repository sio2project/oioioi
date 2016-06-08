from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.teachers.menu import teacher_menu_registry

teacher_menu_registry.register('teacher_dashboard', _("Contests"),
                               lambda request: reverse('teacher_dashboard'),
                               order=5)
