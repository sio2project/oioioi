from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import ugettext as _

from oioioi.usergroups.models import UserGroupRanking
from oioioi.rankings.models import Ranking
from oioioi.usergroups.controllers import USER_GROUP_RANKING_PREFIX


class Command(BaseCommand):
    help = _("Remove user group rankings from database")

    @transaction.atomic
    def handle(self, *args, **options):
        key_infix = '#' + USER_GROUP_RANKING_PREFIX

        Ranking.objects.filter(key__contains=key_infix).delete()
        UserGroupRanking.objects.all().delete()
