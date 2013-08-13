from django.utils.translation import ugettext_lazy as _
from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.models import submission_statuses


check_django_app_dependencies(__name__, ['oioioi.participants'])


submission_statuses.register('IGN', _("Ignored"))
