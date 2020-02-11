import time
import traceback

from django.core.mail import mail_admins
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
import requests

from oioioi.ipauthsync.models import (
    IpAuthSyncConfig,
    IpAuthSyncedUser,
    IpAuthSyncRegionMessages,
)
from oioioi.ipdnsauth.models import IpToUser
from oioioi.participants.models import OnsiteRegistration


class Command(BaseCommand):
    help = "Synchronizes the IP authentication database with region servers."

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            default=60,
            type=int,
            help="Time between synchronization rounds",
        )
        parser.add_argument(
            '--timeout',
            metavar='SECONDS',
            default=15,
            type=int,
            help="Connection timeout",
        )

    def handle_config(self, config):
        rc = config.contest.controller.registration_controller()
        for region in config.contest.regions.all():
            try:
                r = requests.get(
                    f'http://{region.region_server}/ipauthsync/list',
                    headers=dict(Host='oireg'),
                )
                r.raise_for_status()

                warnings = []
                mapping = []
                for item in r.json()['mappings']:
                    zaw_id = item['user_id']
                    ip = item['ip_address']
                    try:
                        reg = OnsiteRegistration.objects.select_related(
                            'participant__user'
                        ).get(number=zaw_id, region=region)
                        user = reg.participant.user
                    except OnsiteRegistration.DoesNotExist:
                        warnings.append(
                            "* No user found for ZAW=%s (IP=%s)" % (zaw_id, ip)
                        )
                        continue

                    try:
                        rc.ipauthsync_validate_ip(region, ip, user)
                    # pylint: disable=broad-except
                    except Exception as e:
                        warnings.append("Invalid IP=%s (ZAW=%s): %s" % (ip, zaw_id, e))

                    mapping.append('%s %s %s' % (zaw_id, ip, user.username))

                    yield user, ip

                warnings = '\n'.join(warnings)
                mapping = '\n'.join(mapping)
                msgs, created = IpAuthSyncRegionMessages.objects.get_or_create(
                    region=region
                )
                if warnings != msgs.warnings:
                    msgs.warnings = warnings
                    msgs.save()
                    mail_admins(
                        "ipauthsyncd: Warnings for region %s" % (region.short_name,),
                        warnings,
                    )
                if mapping != msgs.mapping:
                    msgs.mapping = mapping
                    msgs.save()
                    mail_admins(
                        "ipauthsyncd: Mapping for region %s" % (region.short_name,),
                        mapping,
                    )

                if region.short_name in self.failing_regions:
                    self.failing_regions.remove(region.short_name)
                    mail_admins(
                        "ipauthsyncd: Sync now OK for region %s" % (region.short_name,),
                        "(Intentionally left blank)",
                    )
            # pylint: disable=broad-except
            except Exception:
                if region.short_name in self.failing_regions:
                    continue
                self.failing_regions.add(region.short_name)
                mail_admins(
                    "ipauthsyncd: Sync failing for region %s" % (region.short_name,),
                    traceback.format_exc(),
                )

    def handle(self, *args, **options):
        # pylint: disable=attribute-defined-outside-init
        self.options = options
        # pylint: disable=attribute-defined-outside-init
        self.failing_regions = set()
        while True:
            configs = (
                IpAuthSyncConfig.objects.get_active(timezone.now())
                .select_related('contest')
                .prefetch_related('contest__regions')
            )
            mappings = []
            for c in configs:
                mappings.extend(self.handle_config(c))

            with transaction.atomic():
                IpToUser.objects.filter(ipauthsynceduser__isnull=False).delete()
                IpAuthSyncedUser.objects.all().delete()
                for user, ip in mappings:
                    entry = IpToUser(user=user, ip_addr=ip)
                    entry.save()
                    IpAuthSyncedUser(entry=entry).save()

            time.sleep(options['interval'])
