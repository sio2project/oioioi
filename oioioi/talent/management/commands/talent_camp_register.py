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

def str_to_time(s):
    return map(int, s.split(':'))

class Command(BaseCommand):
    help = _("Add users to contests and supervision groups at Stowarzyszenie Talent's camps")
    
    def add_arguments(self, parser):
        parser.add_argument('-c', action='store_true', default=False,
                            dest='commit', help="Commit changes, not just print them")
    
    def handle(self, *args, **options):
        run(["sed", "-i", 
                "s/#*TALENT_REGISTRATION_CLOSED.*$/TALENT_REGISTRATION_CLOSED = True/", "/sio2/deployment/settings.py"], check=True)
        run(["/sio2/deployment/manage.py", "supervisor", "--skip-checks", "restart", "uwsgi"], check=True)
        
        commit=options['commit']
        print("{: <13}{: <13} {: <13} {: <13}".format("Group", "Username", "First name", "Last name")) 
        with transaction.atomic():
            for r in TalentRegistration.objects.filter():
                group=Group.objects.get(name=settings.TALENT_CONTEST_NAMES[r.group])
                contest=Contest.objects.get(id=r.group)
                user=r.participant.user
                if commit:
                    Participant.objects.get_or_create(contest=contest, user=user)
                    Membership.objects.get_or_create(user=user, group=group, is_present=True)
                print("{: <13}{: <13} {: <13} {: <13}".format(r.group.upper(), user.username, user.first_name, 
                                                     user.last_name))
        if commit:
            print("\n--- Added users to groups and contests:")
            for id, name in settings.TALENT_CONTEST_NAMES.items():
                contest=Contest.objects.get(id=id)
                print(Participant.objects.filter(contest=contest).count(), "in " + name)
        else:
            print("\n--- If all looks good, run this with -c")
