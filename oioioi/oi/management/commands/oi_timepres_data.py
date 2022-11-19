import sys

import unicodecsv
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from pytz import timezone

from oioioi.contests.models import Contest, Submission


class Command(BaseCommand):
    help = _("Export data for oi-timepres final presentation.")

    requires_model_validation = True

    def add_arguments(self, parser):
        parser.add_argument('contest_id', type=str)
        parser.add_argument('output_file', type=str)
        parser.add_argument('user_list', type=str, nargs='+')

    def handle(self, *args, **options):
        contest = Contest.objects.get(id=options['contest_id'])
        out_file = options['output_file']
        logins_to_show = options['user_list']

        users = User.objects.filter(username__in=logins_to_show)
        all_submissions = (
            Submission.objects.filter(user__in=users)
            .filter(problem_instance__contest=contest)
            .filter(score__isnull=False)
            .order_by('date')
        )

        warsaw = timezone('Europe/Warsaw')
        rows = []
        for s in all_submissions:
            e = [
                s.date.astimezone(warsaw).strftime('%Y-%m-%d %H:%M:%S'),
                str(s.user),
                s.user.get_full_name(),
                s.problem_instance.problem.short_name,
                str(s.score.value),
            ]
            rows.append(e)

        with open(out_file, 'w') as f:
            csv = unicodecsv.writer(f)
            csv.writerows(rows)

        sys.stdout.write(_("Ok, written %d rows") % len(rows))
