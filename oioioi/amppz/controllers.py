from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from oioioi.acm.controllers import ACMContestController
from oioioi.contests.utils import is_contest_admin, is_contest_observer


class AMPPZContestController(ACMContestController):
    description = _("AMPPZ")
    create_forum = False

    def can_see_ranking(self, request):
        return is_contest_admin(request) or is_contest_observer(request)

    def default_contestlogo_url(self):
        return '%samppz/images/logo-cropped.png' % settings.STATIC_URL

    def default_contesticons_urls(self):
        return ['%samppz/images/menu-icon.png' % settings.STATIC_URL]
