import six
from subprocess import run

from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.conf import settings
from oioioi.participants.models import Participant
from oioioi.contests.models import Contest
from oioioi.supervision.models import Membership
from django.db import transaction

def member_qs(user):
    return Membership.objects.filter(user=user).select_related('group')

def part_qs(user):
    return Participant.objects.filter(contest__controller_name= \
        'oioioi.phase.controllers.PhaseContestController', user=user) \
        .select_related('contest')

def id_from_group(group):
    for id, name in settings.TALENT_CONTEST_NAMES.items():
        if name==group.name:
            return id
    raise KeyError

class Command(BaseCommand):
    help = _("View users added tp contests and supervision groups at Stowarzyszenie Talent's camps")
    
    def add_arguments(self, parser):
        parser.add_argument('-c', action='store_true', default=False,
                            dest='close', help="Close the registration")
        parser.add_argument('-o', action='store_true', default=False,
                            dest='open', help="Open the registration")
    
    def handle(self, *args, **options):
        registration_change=None
        if options['close']:
            registration_change="True"
        if options['open']:
            if registration_change!=None:
                print("You can't open AND close the registration!")
                return
            registration_change="False"
        if registration_change!=None:
            run(["sed", "-i", 
                    "s/#*TALENT_REGISTRATION_CLOSED.*$/TALENT_REGISTRATION_CLOSED = " + registration_change + "/", "/sio2/deployment/settings.py"], check=True)
            run(["/sio2/deployment/manage.py", "supervisor", "--skip-checks", "restart", "uwsgi"], check=True)
        
        users_unassigned = tuple()
        users_wrong = tuple()
        print("\n--- Users registered correctly ---\n")
        print("{: <15}{: <15} {: <15} {: <15}".format("Group", "Username", "First name", "Last name")) 
        for user in User.objects.filter(is_superuser=False):
            if not member_qs(user).exists() and not part_qs(user).exists():
                users_unassigned+=(user,)
                continue
            if part_qs(user).count()!=1:
                users_wrong+=(user,)
                continue
            
            contestid=part_qs(user).get().contest.id
            if contestid in settings.TALENT_SUPERVISED_IDS:
                if member_qs(user).count()!=1 or id_from_group(member_qs(user).get().group)!=contestid or not member_qs(user).get().is_present:
                    users_wrong+=(user,)
                    continue
            else:
                if member_qs(user).count()!=0:
                    users_wrong+=(user,)
                    continue
                
            print("{: <15}{: <15} {: <15} {: <15}".format(contestid.upper(),
                                                          user.username,
                                                          user.first_name,
                                                          user.last_name))
        
        print("\n\n--- Superusers ---\n")
        for user in User.objects.filter(is_superuser=True):
            print(user.username)
        
        if len(users_unassigned):
            print("\n\n--- Unassigned users ---\n")
            print("{: <15} {: <15} {: <15}".format("Username", "First name", "Last name")) 
            for user in users_unassigned:
                print("{: <15} {: <15} {: <15}".format(user.username, user.first_name, user.last_name))
        
        if len(users_wrong):
            print("\n\n--- Misassigned users (lowercase group means not present) ---\n")
            print("{: <15} {: <15} {: <15} {: <15} {: <15}".format("Username", "First name", "Last name", "Groups", "Contests"))
            for user in users_wrong:
                groups=[]
                for member in member_qs(user):
                    if member.is_present:
                        groups+=[id_from_group(member.group).upper(),]
                    else:
                        groups+=[id_from_group(member.group),]
                participants=[ participant.contest.id.upper() for participant in part_qs(user) ]
                print("{: <15} {: <15} {: <15} {: <15} {: <15}".format(user.username, user.first_name, user.last_name, ','.join(groups), ','.join(participants)))
        
        if registration_change!=None:
            if registration_change=="True":
                status="CLOSED"
            else:
                status="OPEN"
        else:
            if settings.TALENT_REGISTRATION_CLOSED:
                status="CLOSED"
            else:
                status="OPEN"
        print("\n\n--- Registration status:", status, "\n");
