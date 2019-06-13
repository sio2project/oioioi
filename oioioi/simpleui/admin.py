from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.menu import personal_menu_registry

personal_menu_registry.register('teacher_dashboard', _("Contests"),
                               lambda request: reverse('teacher_dashboard'),
                               lambda request: request.user.has_perm('teachers.teacher'),
                               order=5)
