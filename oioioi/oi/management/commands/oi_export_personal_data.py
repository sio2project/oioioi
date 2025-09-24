import sys

import unicodecsv
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from oioioi.participants.models import Participant

COLUMNS = [
    ("user", "", ["id", "username", "first_name", "last_name"]),
    (
        "registration_model",
        "",
        [
            "address",
            "postal_code",
            "city",
            "phone",
            "birthday",
            "birthplace",
            "t_shirt_size",
            "class_type",
            "terms_accepted",
            (
                "school",
                "school",
                [
                    "name",
                    "address",
                    "postal_code",
                    "city",
                    "province",
                    "phone",
                    "email",
                ],
            ),
        ],
    ),
]


class Command(BaseCommand):
    help = _("Export personal data.")

    def add_arguments(self, parser):
        parser.add_argument("contest_id", type=str, help="Contest to export from")
        parser.add_argument("out_file", type=str, help="File path to export to")

    def gen_csv_header(self):
        def render_sublist(sublist, prefix):
            result = []
            for field in sublist:
                if isinstance(field, tuple):
                    result.extend(render_sublist(field[2], prefix + field[1] + "_" if field[1] else prefix))
                else:
                    result.append(prefix + field)
            return result

        return render_sublist(COLUMNS, "")

    def collect_personal_data(self, contest_id, **kwargs):
        def render_sublist(sublist, model):
            result = []
            for field in sublist:
                if isinstance(field, tuple):
                    result.extend(render_sublist(field[2], getattr(model, field[0])))
                else:
                    result.append(getattr(model, field))
            return result

        participants = Participant.objects.filter(contest=contest_id)
        return [render_sublist(COLUMNS, p) for p in participants]

    def handle(self, *args, **options):
        contest_id = options["contest_id"]
        out_file = options["out_file"]

        csv_header = self.gen_csv_header()

        personal_data = self.collect_personal_data(contest_id, **options)

        with open(out_file, "w") as f:
            csv = unicodecsv.writer(f)
            csv.writerow(csv_header)
            csv.writerows(personal_data)

        sys.stdout.write(_("Ok, written %d rows") % len(personal_data))
