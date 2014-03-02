import json
import time
import sys
from operator import itemgetter
from itertools import groupby

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext as _
from django.db import transaction

from oioioi import evalmgr
from oioioi.zeus.backends import get_zeus_server
from oioioi.zeus.models import ZeusAsyncJob


class Command(BaseCommand):
    help = _("Fetches grading results from Zeus")

    requires_model_validation = True

    def handle(self, *args, **options):
        zeus_server_id = ''
        raise NotImplementedError
        zeus = get_zeus_server(zeus_server_id)

        while True:
            # TODO: Simulate fetching results
            with transaction.commit_on_success():
                # TODO: use seq, save it somewhere etc.
                received_results = zeus.fetch_results()
                for check_uid, reports in \
                        groupby(received_results, itemgetter('check_uid')):
                    try:
                        env_obj = ZeusAsyncJob.objects.get(check_uid=check_uid)
                    except ZeusAsyncJob.DoesNotExist as e:
                        # WTF?, TODO: think of race-condition
                        continue

                    sys.stdout.write(_("Got new results for: %s\n") % check_uid)
                    environ = json.loads(env_obj.environ)
                    environ.setdefault('zeus_results', [])
                    environ['zeus_results'].extend(list(reports))
                    _async_result = evalmgr.evalmgr_job.delay(environ)
                    #TODO: postpone handlers?
                    env_obj.delete()
            sys.stderr.write(_("Waiting for new results...\n"))
            time.sleep(10)
