from __future__ import print_function

import six
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from oioioi.base.notification import NotificationHandler
from oioioi.contests.models import Contest


class Command(BaseCommand):
    help = "Sends a notification to selected users"
    requires_model_validation = False

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '-c',
            '--contest',
            type=six.text_type,
            action='store',
            help="notifies all participants of a contest",
        )
        group.add_argument(
            '-u',
            '--user',
            type=six.text_type,
            action='store',
            help="notifies particular user",
        )

        parser.add_argument(
            '-p',
            '--popup',
            action='store_true',
            help="make the notification pop-up automatically",
        )
        parser.add_argument(
            '-a', '--address', type=six.text_type, action='store', help="adds a link"
        )
        parser.add_argument(
            '-d',
            '--details',
            type=six.text_type,
            action='store',
            help="adds message details",
        )
        parser.add_argument('message', type=str, nargs='+')

    def handle(self, *args, **options):
        message = ' '.join(options['message'])
        if options['user']:
            try:
                users = [User.objects.get(username=options['user'])]
            except User.DoesNotExist:
                raise CommandError("specified user does not exist")
        elif options['contest']:
            try:
                contest = Contest.objects.get(name=options['contest'])
                users = (
                    contest.controller.registration_controller().filter_participants(
                        User.objects.all()
                    )
                )
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
                user, 'custom_notification', message, arguments
            )
            print("Notification sent to", user.username)
