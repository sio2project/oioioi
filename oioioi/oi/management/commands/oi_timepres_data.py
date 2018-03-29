import sys

import unicodecsv
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from pytz import timezone

from oioioi.contests.models import Contest, Submission


class Command(BaseCommand):
    args = _("<contest_id> <output_file> <user1> [<user2> ...]")
    help = _("Export data for oi-timepres final presentation.")

    requires_model_validation = True

    def handle(self, *args, **options):
        if len(args) < 3:
            raise CommandError(_("Expected contest_id, output_file"
                                 " and non-empty list of usernames"))

        contest = Contest.objects.get(id=args[0])
        out_file = args[1]
        logins_to_show = args[2:]

        users = User.objects.filter(username__in=logins_to_show)
        all_submissions = Submission.objects \
                .filter(user__in=users) \
                .filter(problem_instance__contest=contest) \
                .filter(score__isnull=False) \
                .order_by('date')

        warsaw = timezone('Europe/Warsaw')
        rows = []
        for s in all_submissions:
            e = [
                s.date.astimezone(warsaw).strftime('%Y-%m-%d %H:%M:%S'),
                str(s.user),
                s.user.get_full_name(),
                s.problem_instance.problem.short_name,
                str(s.score.value)
            ]
            rows.append(e)

        with open(out_file, 'w') as f:
            csv = unicodecsv.writer(f)
            csv.writerows(rows)

        sys.stdout.write(_("Ok, written %d rows") % len(rows))
