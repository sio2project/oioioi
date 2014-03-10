import json
import time
import logging
import traceback
from operator import itemgetter
from itertools import groupby

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext as _
from django.db import transaction
from django.conf import settings

from oioioi import evalmgr
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
            except StandardError as e:
                logger.error("Error occured:\n%s", traceback.format_exc(e))
            else:
                if seq is not None:
                    zeus.commit_fetch(seq)

            logger.debug("Waiting for new results...")
            time.sleep(10)

    @transaction.commit_on_success
    def fetch_once(self, zeus):
        try:
            seq, received_results = zeus.fetch_results()
        except ZeusError as e:
            logger.error("Zeus error occured:\n%s", traceback.format_exc(e))
            return None

        for check_uid, reports in \
                groupby(received_results, itemgetter('check_uid')):
            try:
                env_obj = ZeusAsyncJob.objects.get(check_uid=check_uid)
            except ZeusAsyncJob.DoesNotExist:
                #TODO: think of race-condition
                #TODO: we may get the same results more then once
                continue

            logger.info("Got new results for: %s", check_uid)
            environ = json.loads(env_obj.environ)
            environ.setdefault('zeus_results', [])
            environ['zeus_results'].extend(list(reports))
            _async_result = evalmgr.evalmgr_job.delay(environ)
            #TODO: postpone handlers?
            env_obj.delete()
        return seq
