import datetime

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from oioioi.acm.controllers import ACMContestController
from oioioi.contests.utils import is_contest_admin, is_contest_observer


class AMPPZContestController(ACMContestController):
    description = _("AMPPZ")
    create_forum = False

    def get_round_freeze_time(self, round):
        """Returns time after which any further updates should be non-public."""
        if not round.end_date:
            return None
        if round.is_trial:
            frozen_ranking_minutes = 15
        else:
            frozen_ranking_minutes = 60

        return round.end_date - datetime.timedelta(minutes=frozen_ranking_minutes)

    def default_can_see_statement(self, request_or_context, problem_instance):
        return False

    def can_see_livedata(self, request):
        return True

    def default_can_see_ranking(self, request):
        return is_contest_admin(request) or is_contest_observer(request)

    def default_contestlogo_url(self):
        return '%samppz/images/logo-cropped.png' % settings.STATIC_URL

    def default_contesticons_urls(self):
        return ['%samppz/images/menu-icon.png' % settings.STATIC_URL]
