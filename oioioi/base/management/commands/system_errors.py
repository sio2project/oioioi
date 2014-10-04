from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _

from oioioi.contests.models import FailureReport, Contest


class Command(BaseCommand):

    args = _("[contest_id]")
    help = _("List submissions graded as SE")

    requires_model_validation = True

    def handle(self, *args, **options):
        c = None
        if len(args) > 1:
            raise CommandError(_("Expected at most one argument"))
        if len(args) == 1:
            c = Contest.objects.get(id=args[0])

        frs = FailureReport.objects.filter(submission_report__status='ACTIVE')

        if c is not None:
            kwargs = {'submission_report__submission'
                      '__problem_instance__contest': c}
            frs = frs.filter(**kwargs)

        frs.select_related('submission_report',
                           'submission_report__submission',
                           'submission_report__submission__problem_instance')

        out = []

        for fr in frs:
            sub = fr.submission_report.submission
            pi = sub.problem_instance
            row = []
            if c is None:
                row.append(pi.contest_id)
            row += [sub.id, sub.user, pi.short_name]
            out.append(row)

        self.pprint(out)

    def pprint(self, rows):
        if not rows:
            return
        widths = [0] * len(rows[0])
        for row in rows:
            assert len(row) == len(widths)
            row[:] = map(str, row)
            for i, val in enumerate(row):
                widths[i] = max(widths[i], len(val))

        for row in rows:
            for i, val in enumerate(row):
                print val.ljust(widths[i]),
            print ''
