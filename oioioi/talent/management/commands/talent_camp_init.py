from datetime import timedelta
from getpass import getpass
import pytz
from subprocess import run

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from oioioi.contests.models import Contest, Round
from oioioi.dashboard.models import DashboardMessage
from oioioi.phase.models import Phase
from oioioi.questions.models import MessageNotifierConfig
from oioioi.scoresreveal.models import ScoreRevealContestConfig
from oioioi.supervision.models import Supervision, Group
from oioioi.talent.models import TalentRegistrationSwitch

User = get_user_model()
def createsuperuser(username, password="", email="", first_name="", last_name=""):
    if User.objects.filter(username=username).exists():
        print("User {} already exists!".format(username))
        return
    if len(password)<1:
        password = getpass("Password for {}: ".format(username))
        password2 = getpass("Password for {} (again): ".format(username))
        while password!=password2 or len(password)<1:
            print("The passwords don't match! Try again.")
            password = getpass("Password for {}: ".format(username))
            password2 = getpass("Password for {} (again): ".format(username))
    User.objects.create_superuser(username, email, password, first_name=first_name, last_name=last_name)


class Command(BaseCommand):
    help = _(
        "Create contests, rounds, etc. for Stowarzyszenie Talent's camps"
    )

    def handle(self, *args, **options):

        with transaction.atomic():
            print("--- Creating default superusers")
            for user, password, email, first_name, last_name in settings.TALENT_DEFAULT_SUPERUSERS:
                createsuperuser(user, password, email, first_name, last_name)

            today = timezone.localtime(timezone=pytz.timezone(settings.TIME_ZONE))
            today = today.replace(microsecond=0, second=0, minute=0, hour=0)
            contest_names = settings.TALENT_CONTEST_NAMES

            print("--- Creating contests, rounds, etc.")
            # Contests
            for i in settings.TALENT_CONTEST_IDS:
                if i in settings.TALENT_CLOSED_CONTEST_IDS:
                    controller="oioioi.talent.controllers.TalentContestController"
                else:
                    controller="oioioi.talent.controllers.TalentOpenContestController"
                contest, _ = Contest.objects.get_or_create(
                    id=i,
                    name=contest_names[i],
                    controller_name=controller,
                )
                # Rounds
                for roundnum, daynum in settings.TALENT_CONTEST_DAYS:
                    cday = today + timedelta(days=daynum)
                    name = "Dzień " + str(roundnum)
                    round_start = cday + settings.TALENT_CONTEST_START[i]
                    round_end = cday + settings.TALENT_CONTEST_END[i]
                    round_results = cday + settings.TALENT_CONTEST_RESULTS[i]
                    Round.objects.update_or_create(
                        contest=contest,
                        name=name,
                        defaults={
                            "start_date": round_start,
                            "end_date": round_end,
                            "results_date": round_results,
                        }                        
                    )
            # Trial contest & round (it's last to become the default contest)
            contest, _ = Contest.objects.get_or_create(
                id="p",
                name="Kontest próbny",
                controller_name='oioioi.talent.controllers.TalentOpenContestController',
            )
            Round.objects.update_or_create(
                contest=contest,
                name="Runda próbna",
                defaults={
                    "start_date": today,
                    "results_date": today,
                }                
            )
            DashboardMessage.objects.update_or_create(
                contest=Contest.objects.get(id="p"),
                defaults={
                    "content": settings.TALENT_DASHBOARD_MESSAGE,
                }
            )
            # Supervision groups
            for i in settings.TALENT_SUPERVISED_IDS:
                group, _ = Group.objects.get_or_create(name=contest_names[i])
                # Supervisions
                for r in Round.objects.filter(contest_id=i):
                    Supervision.objects.update_or_create(
                        group=group,
                        round=r,
                        defaults={
                            "start_date": r.start_date,
                            "end_date": r.end_date,
                        }
                    )
            # Phases
            for r in Round.objects.filter(contest_id__in=settings.TALENT_PHASED_IDS):
                Phase.objects.update_or_create(
                    round=r,
                    defaults={
                        "start_date": r.end_date,
                        "multiplier": settings.TALENT_SCORE1,
                    }
                    
                )
                Phase.objects.update_or_create(
                    round=r,
                    defaults={
                        "start_date": r.start_date \
                            - settings.TALENT_CONTEST_START[r.contest_id] \
                            + settings.TALENT_PHASE2_END,
                        "multiplier": settings.TALENT_SCORE2,
                    }
                )
            # Default score reveal configs
            for id,limit in settings.TALENT_DEFAULT_SCOREREVEALS.items():
                ScoreRevealContestConfig.objects.update_or_create(
                    contest=Contest.objects.get(id=id),
                    defaults={
                        "reveal_limit": limit,
                    }
                )
            # Notified-about-new-questions configs
            for login, contestids in settings.TALENT_MAIL_NOTIFICATIONS.items():
                user = User.objects.get(username=login)
                for cid in contestids:
                    MessageNotifierConfig.objects.update_or_create(
                        contest_id=cid, 
                        defaults={
                            "user": user,
                        }
                    )
            # Enable talent registration (automatic assigning to groups)
            TalentRegistrationSwitch.objects.get_or_create(status=True)

        print("--- Finished!")
