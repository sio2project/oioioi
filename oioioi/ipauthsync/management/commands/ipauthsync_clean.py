from django.core.management.base import NoArgsCommand
from django.db import transaction

from oioioi.ipdnsauth.models import IpToUser
from oioioi.ipauthsync.models import IpAuthSyncedUser


class Command(NoArgsCommand):
    help = "Removes synced entries from the IP database."

    def handle_noargs(self, **options):
        with transaction.atomic():
            IpToUser.objects.filter(ipauthsynceduser__isnull=False) \
                    .delete()
            IpAuthSyncedUser.objects.all().delete()
