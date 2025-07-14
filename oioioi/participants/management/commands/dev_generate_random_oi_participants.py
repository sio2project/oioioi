import os
import random
import urllib.request
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from django.utils.translation import gettext as _

from oioioi.contests.models import Contest
from oioioi.oi.models import CLASS_TYPES, T_SHIRT_SIZES, OIRegistration, School
from oioioi.participants.models import Participant


class Command(BaseCommand):
    help = _(
        "Imports users and adds them as participants to <contest_id>.\n"
        "The users do not need to be in the database, they will be inserted dynamically.\n"
        "There should exist some School objects in database. If not, you can generate them with import_schools.py\n"
        "Each line must have: username first_name last_name (space or comma separated).\n"
        "Lines starting with '#' are ignored."
    )

    def add_arguments(self, parser):
        parser.add_argument("contest_id", type=str, help="Contest to import to")
        parser.add_argument("filename_or_url", type=str, help="Source file")

    def handle(self, *args, **options):
        try:
            contest = Contest.objects.get(id=options["contest_id"])
        except Contest.DoesNotExist:
            raise CommandError(_("Contest %s does not exist") % options["contest_id"])

        arg = options["filename_or_url"]
        if arg.startswith("http://") or arg.startswith("https://"):
            self.stdout.write(_("Fetching %s...\n") % (arg,))
            stream = urllib.request.urlopen(arg)
            stream = (line.decode("utf-8") for line in stream)
        else:
            if not os.path.exists(arg):
                raise CommandError(_("File not found: %s") % arg)
            stream = open(arg, encoding="utf-8")

        schools = list(School.objects.all())
        if not schools:
            raise CommandError("No schools found in the database.")

        all_count = 0
        with transaction.atomic():
            ok = True
            for line in stream:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.replace(",", " ").split()
                if len(parts) != 3:
                    self.stdout.write(_("Invalid line format: %s\n") % line)
                    ok = False
                    continue

                username, first_name, last_name = parts

                try:
                    user, created = User.objects.get_or_create(username=username)
                    if created:
                        user.first_name = first_name
                        user.last_name = last_name
                        user.set_unusable_password()
                        user.save()

                    Participant.objects.get_or_create(contest=contest, user=user)
                    participant, extra = Participant.objects.get_or_create(contest=contest, user=user)

                    OIRegistration.objects.create(
                        participant=participant,
                        address=f"ulica {random.randint(1, 100)}",
                        postal_code=f"{random.randint(10, 99)}-{random.randint(100, 999)}",
                        city=f"Miasto{random.randint(1, 50)}",
                        phone=f"+48 123 456 {random.randint(100, 999)}",
                        birthday=date.today() - timedelta(days=random.randint(5000, 8000)),
                        birthplace=f"Miejsce{random.randint(1, 100)}",
                        t_shirt_size=random.choice(T_SHIRT_SIZES)[0],
                        class_type=random.choice(CLASS_TYPES)[0],
                        school=random.choice(schools),
                        terms_accepted=True,
                    )
                    all_count += 1
                except DatabaseError as e:
                    self.stdout.write(_("DB Error for user=%s: %s\n") % (username, str(e)))
                    ok = False

            if ok:
                print(f"Successfully processed {all_count} entries.")
            else:
                raise CommandError(_("There were some errors. Database not changed."))
