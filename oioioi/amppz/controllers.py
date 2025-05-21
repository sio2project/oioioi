import datetime

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from oioioi.acm.controllers import ACMContestController
from oioioi.contests.utils import is_contest_admin, is_contest_observer


class AMPPZContestController(ACMContestController):
    description = _("AMPPZ")
    create_forum = False
    scoring_description = _(
        "The solutions are judged on real-time. "
        "The submission is correct if it passes all the test cases.\n"
        "Participants are ranked by the number of solved problems. "
        "In case of a tie, the times of first correct submissions are summed up and a penalty of 20 minutes is added for each incorrect submission.\n"
        "The lower the total time, the higher the rank.\n"
        "Compilation errors and system errors are not considered as an incorrect submission.\n"
        "The ranking is frozen 15 minutes before the end of the trial rounds and 60 minutes before the end of the normal rounds."
        )

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
