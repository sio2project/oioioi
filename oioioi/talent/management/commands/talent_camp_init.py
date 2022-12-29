import six
from subprocess import run
import pytz

from django.utils.translation import gettext_lazy as _
from django.core.management.base import BaseCommand
from django.conf import settings
from oioioi.contests.models import Contest, Round
from oioioi.dashboard.models import DashboardMessage
from oioioi.phase.models import Phase
from oioioi.supervision.models import Supervision, Group
from oioioi.talent.models import TalentRegistrationSwitch
from django.db import transaction, DatabaseError
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = _(
        "Create contests, phases and supervisions for Stowarzyszenie Talent's camps"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '-f',
            action='store_true',
            default=False,
            dest='force',
            help="Force (Don't quit on DB Errors)",
        )

    def handle(self, *args, **options):
        
        today = timezone.localtime(timezone=pytz.timezone(settings.TIME_ZONE))
        today = today.replace(microsecond=0, second=0, minute=0, hour=0)

        contest_names = settings.TALENT_CONTEST_NAMES
        
        try:
            with transaction.atomic():
                # Enable talent registration (automatic assigning to groups)
                TalentRegistrationSwitch.objects.get_or_create(status=True)
                # Kontest próbny
                contest, _ = Contest.objects.get_or_create(
                    id="p",
                    name="Kontest próbny",
                    controller_name='oioioi.talent.controllers.TalentOpenContestController',
                    default_submissions_limit=150,
                )
                DashboardMessage.objects.get_or_create(
                    contest=Contest.objects.get(id="p"), content=settings.TALENT_DASHBOARD_MESSAGE
                )
                Round.objects.get_or_create(
                    contest=contest,
                    name="Runda próbna",
                    start_date=today,
                    results_date=today,
                )
                # Kontesty
                for i in settings.TALENT_CONTEST_IDS:
                    contest, _ = Contest.objects.get_or_create(
                        id=i,
                        name=contest_names[i],
                        controller_name="oioioi.talent.controllers.TalentContestController",
                        default_submissions_limit=150,
                    )
                    # Rundy
                    for roundnum, daynum in settings.TALENT_CONTEST_DAYS:
                        cday = today + timedelta(days=daynum)
                        name = "Dzień " + str(roundnum)
                        round_start = cday + settings.TALENT_CONTEST_START[i]
                        round_end = cday + settings.TALENT_CONTEST_END[i]
                        round_results = cday + settings.TALENT_CONTEST_RESULTS[i]
                        Round.objects.get_or_create(
                            contest=contest,
                            name=name,
                            start_date=round_start,
                            end_date=round_end,
                            results_date=round_results,
                        )
                # Grupy kontrol
                for i in settings.TALENT_SUPERVISED_IDS:
                    group, _ = Group.objects.get_or_create(name=contest_names[i])
                    # Kontrole
                    for r in Round.objects.filter(contest_id=i):
                        Supervision.objects.get_or_create(
                            group=group,
                            round=r,
                            start_date=r.start_date,
                            end_date=r.end_date,
                        )
                # Fazy
                for r in Round.objects.filter(contest_id__in=settings.TALENT_PHASED_IDS):
                    Phase.objects.get_or_create(
                        round=r,
                        start_date=r.end_date,
                        multiplier=settings.TALENT_SCORE1,
                    )
                    Phase.objects.get_or_create(
                        round=r,
                        start_date=r.start_date \
                                - settings.TALENT_CONTEST_START[r.contest_id] \
                                + settings.TALENT_PHASE2_END,
                        multiplier=settings.TALENT_SCORE2,
                    )
                
        except DatabaseError:
            print(
                "--- DB Error when creating contests etc.\n"
            )
            if not options['force']:
                raise

        try:
            for user in settings.TALENT_DEFAULT_SUPERUSERS:
                print("Creating superuser " + user + ":")
                run(
                    [
                        "/sio2/deployment/manage.py",
                        "createsuperuser",
                        "--username",
                        user,
                        "--email",
                        "",
                        "--skip-checks",
                    ],
                    capture_output=True,
                )
        except DatabaseError:
            print(
                "--- DB Error when creating default superusers"
                + "\n--- You've probably ran this command already"
            )
            if not options['force']:
                raise

        print(
            "--- Enter additional superuser usernames to create\n"
            + "--- When you're done, press enter at an empty prompt"
        )
        user = input(">>> ")
        try:
            while user != "":
                print("Creating superuser " + user + ":")
                run(
                    [
                        "/sio2/deployment/manage.py",
                        "createsuperuser",
                        "--username",
                        user,
                        "--email",
                        "",
                        "--skip-checks",
                    ],
                    capture_output=True,
                )
                user = input(">>> ")
        except DatabaseError:
            print("--- DB Error when creating additional superusers")
            if not options['force']:
                raise
        
        print("Success!")
