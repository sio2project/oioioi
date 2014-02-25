from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from oioioi.acm.controllers import ACMContestController


class AMPPZContestController(ACMContestController):
    description = _("AMPPZ")
    create_forum = False

    def default_contestlogo_url(self):
        return '%samppz/images/logo-cropped.png' % settings.STATIC_URL

    def default_contesticons_urls(self):
        return ['%samppz/images/menu-icon.png' % settings.STATIC_URL]
