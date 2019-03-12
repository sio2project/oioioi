from __future__ import print_function

import six

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from oioioi.base.notification import NotificationHandler
from oioioi.contests.models import Contest


class Command(BaseCommand):
    args = 'message'
    help = "Sends a notification to selected users"
    requires_model_validation = False
    def add_arguments(self, parser):
        parser.add_argument('-p', '--popup', action='store_true',
                            help="make the notification pop-up automatically")
        parser.add_argument('-c', '--contest', type=six.text_type, action='store',
                            help="notifies all participants of a contest")
        parser.add_argument('-u', '--user', type=six.text_type, action='store',
                            help="notifies particular user")
        parser.add_argument('-a', '--address', type=six.text_type, action='store',
                            help="adds a link")
        parser.add_argument('-d', '--details', type=six.text_type, action='store',
                            help="adds message details")

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
