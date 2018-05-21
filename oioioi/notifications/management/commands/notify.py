from __future__ import print_function

from optparse import make_option

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from oioioi.base.notification import NotificationHandler
from oioioi.contests.models import Contest


class Command(BaseCommand):
    args = 'message'
    help = "Sends a notification to selected users"
    requires_model_validation = False
    option_list = BaseCommand.option_list + (
        make_option('-p', '--popup', action='store_true',
                    help="make the notification pop-up automatically"),
        make_option('-c', '--contest', type='string', action='store',
                    help="notifies all participants of a contest"),
        make_option('-u', '--user', type='string', action='store',
                    help="notifies particular user"),
        make_option('-a', '--address', type='string', action='store',
                    help="adds a link"),
        make_option('-d', '--details', type='string', action='store',
                    help="adds message details"),
    )

    @staticmethod
    def validate_options(*args, **options):
        opts = args[1]
        if opts['contest'] and opts['user']:
            raise CommandError(
                "options --contest and --user are mutually exclusive")
        elif not (opts['contest'] or opts['user']):
            raise CommandError("neither user nor contest provided")

        if len(args[0]) == 0:
            raise CommandError("a message should be provided")

    def handle(self, *args, **options):
        self.validate_options(args, options)

        message = ' '.join(args)
        if options['user']:
            try:
                users = [User.objects.get(username=options['user'])]
            except User.DoesNotExist:
                raise CommandError("specified user does not exist")
        elif options['contest']:
            try:
                contest = Contest.objects.get(name=options['contest'])
                users = contest.controller.registration_controller() \
                    .filter_participants(User.objects.all())
            except Contest.DoesNotExist:
                raise CommandError("specified contest does not exist")

        arguments = {}
        if options['details']:
            arguments.update({'details': options['details']})
        if options['address']:
            arguments.update({'address': options['address']})
        if options['popup']:
            arguments.update({'popup': True})

        for user in users:
            NotificationHandler.send_notification(
                user, 'custom_notification', message, arguments)
            print("Notification sent to", user.username)
