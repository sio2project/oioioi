import json
import time
import logging
from operator import itemgetter
from itertools import groupby

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext as _
from django.db import transaction, IntegrityError
from django.conf import settings

from oioioi.evalmgr.handlers import postpone
from oioioi.zeus.backends import get_zeus_server, ZeusError
from oioioi.zeus.models import ZeusAsyncJob


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = _("Fetches grading results from Zeus")

    requires_model_validation = True

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        zeus_server_ids = settings.ZEUS_INSTANCES.iterkeys()
        self.zeus_servers = {i: get_zeus_server(i) for i in zeus_server_ids}

    def handle(self, *args, **options):
        # TODO: Currently fetcher does not support more than one zeus server.
        assert len(self.zeus_servers) == 1
        zeus = self.zeus_servers.values()[0]
        while True:
            try:
                seq = self.fetch_once(zeus)
            except StandardError:
                logger.error("Error occured while fetching results.",
                             exc_info=True)
            else:
                if seq is not None:
                    zeus.commit_fetch(seq)

            logger.debug("Waiting for new results...")
            time.sleep(settings.ZEUS_RESULTS_FETCH_DELAY)

    @transaction.commit_on_success
    def fetch_once(self, zeus):
        try:
            seq, received_results = zeus.fetch_results()
        except ZeusError:
            logger.error("Zeus error occured.", exc_info=True)
            return None

        for check_uid, reports in \
                groupby(received_results, itemgetter('check_uid')):
            logger.info("Got new results for: %s", check_uid)
            try:
                async_job, created = ZeusAsyncJob.objects.select_for_update() \
                                     .get_or_create(check_uid=check_uid)
            except IntegrityError:
                # This should never happen.
                logger.error("IntegrityError while saving results for %s",
                             check_uid, exc_info=True)
                logger.error("Received reports:\n%s", reports)
                continue
            if async_job.resumed:
                logger.debug("Got results for %s again, ignoring", check_uid)
                continue
            if not created:
                logger.info("Resuming job %s from zeus-fetcher", check_uid)
                env = json.loads(async_job.environ)
                env.setdefault('zeus_results', [])
                env['zeus_results'].extend(list(reports))
                postpone(env)
                async_job.resumed = True
                async_job.save()
            else:
                async_job.environ = json.dumps({'zeus_results': list(reports)})
                async_job.save()

        return seq
