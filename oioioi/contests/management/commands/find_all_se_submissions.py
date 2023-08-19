from __future__ import print_function

import six
import time

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.translation import gettext as _
from django.db import transaction
from oioioi.contests.models import Contest, Round, Submission, SubmissionReport
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = _("Display all submissions that got System Error in the past N days")

    def add_arguments(self, parser):
        parser.add_argument('-n', '--numdays',
                            action='store',
                            type=int,
                            dest='numdays',
                            help="How many past days of reports to check",
                            default=10)

    def handle(self, *args, **options):
        numdays = options["numdays"]
        subs = Submission.objects.filter(date__gte=datetime.now()-timedelta(days=numdays))
        raporty = SubmissionReport.objects.filter(submission__in=subs)
        # problem_instance.controller.judge(submission, is_rejudge=True)
        q = Q(
            failurereport__isnull=False,
        ) | Q(
            testreport__status='SE'
        )
        raporty_z_se = raporty.filter(q).distinct()
        for r in raporty_z_se:
            pi = r.submission.problem_instance

            with transaction.atomic():
                pi.controller.judge(r.submission, is_rejudge=True)
            time.sleep(1)
            print(r.submission.id, end=",")
            print(r.submission, end=",")
            print(pi.contest, ",",  pi.problem, ",", pi.short_name)


