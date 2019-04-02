from __future__ import print_function

from django.core.management.base import BaseCommand
from django.utils.translation import ugettext as _
from six.moves import map

from oioioi.contests.models import Contest, FailureReport
from oioioi.programs.models import TestReport


class Command(BaseCommand):
    help = _("List submissions graded as SE")

    requires_model_validation = True

    def add_arguments(self, parser):
        parser.add_argument('contest_id',
                            nargs='?',
                            default=None,
                            type=str,
                            help='Contest id')

    def handle(self, *args, **options):
        c = options['contest_id']
        if c:
            c = Contest.objects.get(id=c)

        frs = FailureReport.objects.filter(submission_report__status='ACTIVE')
        trs = TestReport.objects.filter(status='SE',
                                        submission_report__status='ACTIVE')

        if c is not None:
            kwargs = {'submission_report__submission'
                      '__problem_instance__contest': c}
            frs = frs.filter(**kwargs)
            trs = trs.filter(**kwargs)

        trs.exclude(submission_report__id__in=[
                fr.submission_report.id for fr in frs])

        frs.select_related('submission_report',
                           'submission_report__submission',
                           'submission_report__submission__problem_instance')

        frs_out, trs_out = [], []

        for fr in frs:
            row = []
            sub = fr.submission_report.submission
            pi = sub.problem_instance
            if c is None:
                row.append(pi.contest_id)
            row += [sub.id, sub.user, pi.short_name]
            frs_out.append(row)

        for tr in trs:
            row = []
            sub = tr.submission_report.submission
            pi = sub.problem_instance
            if c is None:
                row.append(pi.contest_id)
            row += [sub.id, tr.test_name, sub.user, pi.short_name]
            trs_out.append(row)

        print(_("========== Whole submissions =========="))
        self.pprint(frs_out)
        print(_("========== Single tests =========="))
        self.pprint(trs_out)

    def pprint(self, rows):
        if not rows:
            return
        widths = [0] * len(rows[0])
        for row in rows:
            assert len(row) == len(widths)
            row[:] = list(map(str, row))
            for i, val in enumerate(row):
                widths[i] = max(widths[i], len(val))

        for row in rows:
            for i, val in enumerate(row):
                print(val.ljust(widths[i]), end=' ')
            print('')
