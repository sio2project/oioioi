from datetime import timedelta
import pytz
from subprocess import run

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from oioioi.contests.models import Contest, Round
from oioioi.dashboard.models import DashboardMessage
from oioioi.phase.models import Phase
from oioioi.scoresreveal.models import ScoreRevealContestConfig
from oioioi.supervision.models import Supervision, Group
from oioioi.talent.models import TalentRegistrationSwitch


class Command(BaseCommand):
    help = _(
        "Create contests, phases and supervisions for Stowarzyszenie Talent's camps"
    )

    def handle(self, *args, **options):
        
        today = timezone.localtime(timezone=pytz.timezone(settings.TIME_ZONE))
        today = today.replace(microsecond=0, second=0, minute=0, hour=0)

        contest_names = settings.TALENT_CONTEST_NAMES
        
        with transaction.atomic():
            # Enable talent registration (automatic assigning to groups)
            TalentRegistrationSwitch.objects.get_or_create(status=True)
            # Trial contest & round
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
            # Contests
            for i in settings.TALENT_CONTEST_IDS:
                contest, _ = Contest.objects.get_or_create(
                    id=i,
                    name=contest_names[i],
                    controller_name="oioioi.talent.controllers.TalentContestController",
                    default_submissions_limit=150,
                )
                # Rounds
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
            # Supervision groups
            for i in settings.TALENT_SUPERVISED_IDS:
                group, _ = Group.objects.get_or_create(name=contest_names[i])
                # Supervisions
                for r in Round.objects.filter(contest_id=i):
                    Supervision.objects.get_or_create(
                        group=group,
                        round=r,
                        start_date=r.start_date,
                        end_date=r.end_date,
                    )
            # Phases
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
            # Default score reveal configs
            for id,limit in settings.TALENT_DEFAULT_SCOREREVEALS.items():
                ScoreRevealContestConfig.objects.get_or_create(
                    contest=Contest.objects.get(id=id),
                    reveal_limit=limit,
                )

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

        print(
            "--- Enter additional superuser usernames to create\n"
            + "--- When you're done, press enter at an empty prompt"
        )
        user = input(">>> ")
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
        
        print("Success!")
