from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from oioioi.rankings.models import Ranking


class Command(BaseCommand):
    help = _(
        "Mark all rankings as one's needing recalculation."
        "In combination with rankingsd will eventually recalculate all rankings."
    )

    def handle(self, *args, **options):
        Ranking.invalidate_queryset(Ranking.objects.all())
