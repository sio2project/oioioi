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
    help = _("Count submissions in the past N days")

    def add_arguments(self, parser):
        parser.add_argument('-n', '--numdays',
                            action='store',
                            type=int,
                            dest='numdays',
                            help="How many past days of reports to check",
                            default=10)

    def handle(self, *args, **options):
        numdays = options["numdays"]
        subs_all = Submission.objects.filter(date__gte=datetime.now() - timedelta(days=numdays))
        #raporty = SubmissionReport.objects.filter(submission__in=subs)
        # problem_instance.controller.judge(submission, is_rejudge=True)
        for iteration in range(numdays):
            data = (datetime.now() - timedelta(days=iteration)).date()
            q = Q(date__gte=datetime.now() - timedelta(days=iteration)) & Q(date__lte=datetime.now() - timedelta(days=(iteration-1)))
            subs = subs_all.filter(q).count()
            print(str(data) + "," + str(subs))

