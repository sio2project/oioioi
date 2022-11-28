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
from django.db import transaction, DatabaseError
from django.utils import timezone
from datetime import timedelta

def str_to_time(s):
    return map(int, s.split(':'))

class Command(BaseCommand):
    help = _("Create contests, phases and supervisions for Stowarzyszenie Talent's camps")
    
    def add_arguments(self, parser):
        parser.add_argument('-f', action='store_true', default=False,
                            dest='force', help="Force (Don't quit on DB Errors)")
    
    def handle(self, *args, **options):
        site_name = input("--- Camp name: ")
        run(["sed", "-i", 
                "s/^SITE_NAME.*$/SITE_NAME = '" + site_name + "'/",
                "/sio2/deployment/settings.py"], check=True)
        run(["/sio2/deployment/manage.py", "supervisor", "--skip-checks", "restart", "uwsgi", "mailnotifyd"], check=True)
        
        score1 = settings.TALENT_SCORE1
        phase2_end = settings.TALENT_PHASE2_END
        score2 = settings.TALENT_SCORE2
        contest_ids = settings.TALENT_CONTEST_IDS
        regular_contest_ids = settings.TALENT_REGULAR_CONTEST_IDS
        contest_names = settings.TALENT_CONTEST_NAMES
        contest_start = settings.TALENT_CONTEST_START
        contest_end = settings.TALENT_CONTEST_END
        contest_results = settings.TALENT_CONTEST_RESULTS
        default_superusers = settings.TALENT_DEFAULT_SUPERUSERS
        
        nday=timezone.localtime(timezone=pytz.timezone(settings.TIME_ZONE))
        nday=nday.replace(microsecond=0, second=0, minute=0, hour=0)
        
        try:
            with transaction.atomic():
                Contest.objects.create(id="p", name="Kontest próbny", controller_name='oioioi.talent.controllers.TalentTrialContestController', default_submissions_limit=150)
                DashboardMessage.objects.create(contest=Contest.objects.get(id="p"), content=settings.TALENT_DASHBOARD_MESSAGE)
                for i in contest_ids:
                    Contest.objects.create(id=i, name=contest_names[i],
                            controller_name="oioioi.phase.controllers.PhaseContestController",
                            default_submissions_limit=150)
                for i in regular_contest_ids:
                    contest = Contest.objects.get(id=i)
                    group, _ = Group.objects.get_or_create(name=contest_names[i])
                    roundnum = 1
                    for daynum in range(1, 5):
                        cday = nday + timedelta(days=daynum)
                        name = "Dzień " + str(roundnum)
                        round_start = cday + contest_start[i]
                        round_end = cday + contest_end[i]
                        round_results = cday + contest_results[i]
                        round, _ = Round.objects.get_or_create(contest=contest, name=name, 
                                             start_date=round_start, end_date=round_end, 
                                                               results_date=round_results)
                        Phase.objects.create(round=round, start_date=round_end, multiplier=score1)
                        day_end = cday + phase2_end
                        Phase.objects.create(round=round, start_date=day_end, multiplier=score2)
                        Supervision.objects.create(group=group, round=round,
                                                   start_date=round_start, end_date=round_end)
                        roundnum = roundnum + 1
        except DatabaseError:
            print("--- DB Error when creating contests etc." +
                  "\n--- You've probably ran this command already")
            if not options['force']:
                return "Command failed"
        
        try:
            for user in default_superusers:
                print("Creating superuser " + user + ":")
                run(["/sio2/deployment/manage.py", "createsuperuser", 
                                "--username", user, "--email", "", "--skip-checks"],
                               capture_output=True)
        except DatabaseError:
            print("--- DB Error when creating default superusers" +
                  "\n--- You've probably ran this command already")
            if not options['force']:
                return "Command failed"
        
        print("--- Enter additional superuser usernames to create\n" +
              "--- When you're done, press enter at an empty prompt")
        user = input(">>> ")
        try:
            while user != "":
                print("Creating superuser " + user + ":")
                run(["/sio2/deployment/manage.py", "createsuperuser", 
                                "--username", user, "--email", "", "--skip-checks"],
                               capture_output=True)
                user = input(">>> ")
        except DatabaseError:
            print("--- DB Error when creating additional superusers")
            if not options['force']:
                return "Command failed"
