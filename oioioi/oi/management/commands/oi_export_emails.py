import sys

import unicodecsv
from django.core.management.base import BaseCommand
from django.utils.translation import ugettext as _

from oioioi.participants.models import Participant

COLUMNS = ['first_name', 'last_name', 'email']


class Command(BaseCommand):
    help = _("Export personal data.")

    def add_arguments(self, parser):
        parser.add_argument('contest_id',
                            type=str,
                            help="Contest to export from")
        parser.add_argument('out_file',
                            type=str,
                            help="File path to export to")

    def gen_csv_header(self):
        def render_sublist(sublist, prefix):
            result = []
            for field in sublist:
                if isinstance(field, tuple):
                    result.extend(render_sublist(field[2],
                        prefix + field[1] + '_' if field[1] else prefix))
                else:
                    result.append(prefix + field)
            return result

        return render_sublist(COLUMNS, '')

    def collect_personal_data(self, contest_id):
        participants_data = []
        participants = Participant.objects.filter(contest=contest_id)
        for p in participants:
            participants_data.append((p.user.first_name, p.user.last_name, p.user.email))
        return participants_data

    def handle(self, *args, **options):
        contest_id = options['contest_id']
        out_file = options['out_file']

        csv_header = self.gen_csv_header()
        
        personal_data = self.collect_personal_data(contest_id)

        with open(out_file, 'w') as f:
            csv = unicodecsv.writer(f)
            csv.writerow(csv_header)
            for p in personal_data:
                csv.writerow(p)

        sys.stdout.write(_("Ok, written %d rows") % len(personal_data))
