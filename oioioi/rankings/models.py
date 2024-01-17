import pickle
from datetime import timedelta  # pylint: disable=E0611

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from oioioi.base.models import PublicMessage
from oioioi.contests.models import Contest


class RankingRecalc(models.Model):
    pass


class Ranking(models.Model):
    """Represents the state (i.e. is it up to date) and data (both in
    serialized and html formats) for a single ranking.

    For the purposes of this class, we identify the ranking by its contest
    and key. The generated ranking must NOT depend on the request or
    any other ranking.

    This class is responsible only for dealing with WHEN to recalculate
    and to store the serialized data and html for the ranking. Anything
    beyond that should be delegated to RankingController.

    Invalidation is handled explicitly. We assume our ranking is valid,
    until someone else (probably ContestController and friends) tells us
    that something changed. Then the ranking is marked as invalid (not up
    to date) with the help of invalidate_* methods.

    We use _cooldown_ strategy of recalculation. Anytime we regenerate
    ranking we set a cooldown, based on how much time the previous
    recalculation took. If the ranking is invalidated during the cooldown
    period, we don't recalculate until the cooldown period is over.

    Consider the following example of how cooldowns work:

        1) 00:01 - First invalidation event.
                   The ranking is invalid.
        2) 00:02 - The recalculation starts. It didn't start immediately
                   at the time of invalidation, because daemon polls
                   for the rankings needing regeneration so it needed some
                   time to notice.
        3) 00:12 - The recalculation ends, duration was 10 seconds. Ranking
                   is up to date now.
        4) 01:00 - Second invalidation event. Ranking is invalid.
        5) 01:01 - Second recalculation starts.
                   Let's assume RANKING_COOLDOWN_FACTOR = 2.
                   Then the cooldown is 20 seconds, until 01:21
        6) 01:03 - Third invalidation event.
        7) 01:05 - Fourth invalidation event.
        7) 01:08 - Ranking recalculation initiated by the second event ends.
                   Ranking is still invalid, because of the third event.
                   It took 7 seconds.
        8) 01:21 - Cooldown is over. We recalculate ranking because of 3rd
                   and 4th events.
                   The new cooldown is set for 14 seconds, until 01:35.
        9) 01:30 - The recalculation ends.

    The cooldowns can be configured by setting:
    RANKING_COOLDOWN_FACTOR - how long should the cooldown be, related to
                              the last recalculation.
    RANKING_MIN_COOLDOWN - minimum cooldown duration (safety limit)
    RANKING_MAX_COOLDOWN - maximum cooldown duration (safety limit)

    NOTE: We use the local time (and not the database time), for all time
    calculations, including the cooldowns, so be careful about drastic
    changes of system time on the generating machine.
    """

    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    key = models.CharField(max_length=255)

    # advisory
    invalidation_date = models.DateTimeField(auto_now_add=True)
    last_recalculation_date = models.DateTimeField(null=True)

    # used to determine cooldown
    last_recalculation_duration = models.DurationField(default=timedelta(0))

    # internal, use serialized instead
    serialized_data = models.BinaryField(null=True)

    # internal to ranking recalculation mechanism
    # use invalidate_* and is_up_to_date instead
    needs_recalculation = models.BooleanField(default=True)
    cooldown_date = models.DateTimeField(auto_now_add=True)
    recalc_in_progress = models.ForeignKey(
        RankingRecalc, null=True, on_delete=models.SET_NULL
    )

    @property
    def serialized(self):
        """Serialized data of this ranking"""
        if not self.serialized_data:
            return None

        return pickle.loads(self.serialized_data)

    def controller(self):
        """RankingController of the contest"""
        return self.contest.controller.ranking_controller()

    @classmethod
    def invalidate_queryset(cls, qs):
        """Marks queryset of rankings as invalid"""
        qs.all().update(needs_recalculation=True, invalidation_date=timezone.now())

    @classmethod
    def invalidate_contest(cls, contest):
        """Marks all the keys in the constest as invalid"""
        return cls.invalidate_queryset(cls.objects.filter(contest=contest))

    def is_up_to_date(self):
        """Is all the data for this contest up to date (i.e. not invalidated
        since the last recalculation succeeded)?

        If it is not up_to_date we still guarantee that the data is
        in consistent state from the last recalculation.
        """
        return not self.needs_recalculation and self.recalc_in_progress_id is None

    class Meta(object):
        unique_together = ('contest', 'key')


class RankingPage(models.Model):
    """Single page of a ranking"""

    ranking = models.ForeignKey(Ranking, related_name='pages', on_delete=models.CASCADE)
    nr = models.IntegerField()
    data = models.TextField()


def clamp(minimum, x, maximum):
    return max(minimum, min(x, maximum))


@transaction.atomic
def choose_for_recalculation():
    now = timezone.now()
    r = (
        Ranking.objects.filter(needs_recalculation=True, cooldown_date__lt=now)
        .order_by('last_recalculation_date')
        .select_for_update()
        .first()
    )
    if r is None:
        return None
    cooldown_duration = clamp(
        timedelta(seconds=settings.RANKING_MIN_COOLDOWN),
        r.last_recalculation_duration * settings.RANKING_COOLDOWN_FACTOR,
        timedelta(seconds=settings.RANKING_MAX_COOLDOWN),
    )
    r.cooldown_date = now + cooldown_duration
    r.needs_recalculation = False
    recalc = RankingRecalc()
    recalc.save()
    r.recalc_in_progress = recalc
    r.save()
    return recalc


@transaction.atomic
def save_pages(ranking, pages_list):
    ranking.pages.all().delete()
    for nr, page_data in enumerate(pages_list, 1):
        page = RankingPage(ranking=ranking, nr=nr, data=page_data)
        page.save()


@transaction.atomic
def save_recalc_results(recalc, date_before, date_after, serialized, pages_list):
    try:
        r = Ranking.objects.filter(recalc_in_progress=recalc).select_for_update().get()
    except Ranking.DoesNotExist:
        return
    r.serialized_data = pickle.dumps(
        serialized
    )
    save_pages(r, pages_list)
    r.last_recalculation_date = date_before
    r.last_recalculation_duration = date_after - date_before
    old_recalc = r.recalc_in_progress
    r.recalc_in_progress = None
    r.save()
    old_recalc.delete()


def recalculate(recalc):
    date_before = timezone.now()
    try:
        r = (
            Ranking.objects.filter(recalc_in_progress=recalc)
            .select_related('contest')
            .get()
        )
    except Ranking.DoesNotExist:
        return
    ranking_controller = r.controller()
    serialized, pages_list = ranking_controller.build_ranking(r.key)
    date_after = timezone.now()
    save_recalc_results(recalc, date_before, date_after, serialized, pages_list)


class RankingMessage(PublicMessage):
    class Meta(object):
        verbose_name = _("ranking message")
        verbose_name_plural = _("ranking messages")
