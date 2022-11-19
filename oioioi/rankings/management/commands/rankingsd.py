import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from oioioi.rankings.models import choose_for_recalculation, recalculate


class Command(BaseCommand):
    help = _(
        "Daemon that rebuilds rankings. Ranking generation is quite a slow "
        "process, so it is done independently from request, in this daemon. "
        "This allows gracefully handling both the biggest, busiest contests, "
        "and the stale ones."
        "Internally it uses explicit invalidation and eager recalculation "
        "with cooldown."
    )

    def handle(self, *args, **options):
        while True:
            r = choose_for_recalculation()
            if r:
                recalculate(r)
            else:
                time.sleep(settings.RANKINGSD_POLLING_INTERVAL)
