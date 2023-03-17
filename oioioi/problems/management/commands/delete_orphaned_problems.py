import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from oioioi.problems.models import Problem


class Command(BaseCommand):
    help = _("Deletes problems without probleminstances, while skipping those without a contest.")

    def add_arguments(self, parser):
        parser.add_argument(
            '-p',
            action='store_true',
            default=False,
            dest='pretend',
            help='Just pretend to delete the problems',
        )
        parser.add_argument(
            '-a',
            action='store_true',
            default=False,
            dest='all',
            help='Delete even contestless packages',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        pretend = options['pretend']
        problems = Problem.objects.all()
        if not options['all']:
            problems = problems.filter(contest__isnull=False)
        problems = problems.annotate(
                pi_count=Count('probleminstance'),
                ).filter(pi_count=1)
        for p in problems:
            print("Deleting problem " + p.name)
        if not options['pretend']:
            problems.delete()
