import six
from subprocess import run
import pytz

from django.utils.translation import gettext_lazy as _
from django.core.management.base import BaseCommand
from django.conf import settings
from oioioi.participants.models import Participant
from oioioi.contests.models import Contest
from oioioi.supervision.models import Group, Membership
from oioioi.talent.models import TalentRegistration
from django.db import transaction

def member_qs(user):
    return Membership.objects.get(user=user).select_related('group')

def part_qs(user):
    return Participant.objects.filter(contest__controller_name= \
        'oioioi.phase.controllers.PhaseContestController', user=user) \
        .select_related('contest')

class Command(BaseCommand):
    help = _("View users added tp contests and supervision groups at Stowarzyszenie Talent's camps")
    
    def add_arguments(self, parser):
        parser.add_argument('-c', action='store_true', default=False,
                            dest='commit', help="Commit changes, not just print them")
    
    def handle(self, *args, **options):
        run(["sed", "-i", 
                "s/#*TALENT_REGISTRATION_CLOSED.*$/TALENT_REGISTRATION_CLOSED = True/", "/sio2/deployment/settings.py"], check=True)
        run(["/sio2/deployment/manage.py", "supervisor", "--skip-checks", "restart", "uwsgi"], check=True)
        
        commit=options['commit']
        users_unassigned = tuple()
        users_wrong = tuple()
        print("--- Users registered correctly ---\n")
        print("{: <13}{: <13} {: <13} {: <13}".format("Group", "Username", "First name", "Last name")) 
        for user in User.objects.filter(is_superuser=False):
            if not member_qs(user).exists() and not part_qs(user).exists:
                users_unassigned+=(user,)
            elif (member_qs(user).count()!=1 and
                    not (member_qs(user).count()==0 and 
                    part_qs(user).first().contest.id not in settings.TALENT_SUPERVISED_IDS))
                  or part_qs(user).count()!=1:
                users_wrong+=(user,)
            else:
                contest=part_qs(user).get().contest
                print("{: <13}{: <13} {: <13} {: <13}".format(contest.id.upper(),
                                                              user.username,
                                                              user.first_name,
                                                              user.last_name))
        print("\n--- Superusers ---\n")
        for user in User.objects.filter(is_superuser=True):
            print(user.username)
        
        if len(users_unassigned):
            print("\n--- Unassigned users ---\n")
            print("{: <13} {: <13} {: <13}".format("Username", "First name", "Last name")) 
            for user in users_unassigned:
                print("{: <13} {: <13} {: <13}".format(user.username, user.first_name, user.last_name))
        
        if len(users_wrong):
            print("\n--- Misassigned users ---\n")
            print("{: <13} {: <13} {: <13} {: <13} {: <13}".format("Username", "First name", "Last name", "Groups", "Contests"))
            for user in users_wrong:
                groups=[ member.group.name[1] for member in member_qs(user) ]
                participants=[ participant.contest.id.upper() for participant in part_qs(user) ]
                print("{: <13} {: <13} {: <13} {: <13} {: <13}".format(user.username, user.first_name, user.last_name, ','.join(groups), ','.join(participants))
