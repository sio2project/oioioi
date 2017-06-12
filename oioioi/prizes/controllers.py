from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import UserResultForContest
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.prizes.utils import assign_from_order


def by_result_for_contest(pg):
    results = UserResultForContest.objects.select_related('user') \
            .filter(contest=pg.contest, score__isnull=False) \
            .order_by('-score')
    order = []
    prev_score = None
    place = None
    for i, result in enumerate(results, 1):
        if result.score != prev_score:
            place = i
            prev_score = result.score
        order.append((place, result.user))
    assign_from_order(pg, order)


class PrizesControllerMixin(object):
    """ContestController mixin that sets up default settings for prizes app.
    """

    def get_prizes_distributors(self):
        """Returns a dictionary of functions distributing prizes.

           Each funtion takes a PrizeGiving object as the sole argument
           and distributes Prizes to Users within this PrizeGiving through
           creation of appropriate PrizeForUser objects.
           Function may raise AssignmentNotFound. If that's the case,
           all created PrizeForUser objects are deleted and distribution
           fails.
        """
        return {'total_score': (_("total score"), by_result_for_contest)}

    def get_prizes_email_addresses(self, pg):
        """Returns a list of email addresses to which a message will
           be sent, informing about the distribution failure of ``pg``.

           Defaults to empty list.
        """
        return []

    def can_see_prizes(self, request):
        """Determines if the current user is allowed to see awarded prizes.

           By default everybody has access.
        """
        return True

ProgrammingContestController.mix_in(PrizesControllerMixin)
