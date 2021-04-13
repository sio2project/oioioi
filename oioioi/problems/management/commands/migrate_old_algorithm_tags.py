import csv
import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import ugettext as _
from oioioi.problems.models import (
    AlgorithmTag,
    AlgorithmTagLocalization,
    AlgorithmTagThrough,
    Tag,
)


class Command(BaseCommand):
    help = _("Migrates old tags to new algorithm tags.")

    def add_arguments(self, parser):
        parser.add_argument('-f', '--file', type=str)

    @transaction.atomic
    def handle(self, *args, **options):
        filename = options.get('file', '')

        if not filename:
            raise CommandError(_("Filename is obligatory."))

        if not os.path.exists(filename):
            raise CommandError(_("File not found: ") + filename)

        with open(filename, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for row in csv_reader:
                old_tag = Tag.objects.get(name=row['old_name'])
                new_tag, _ = AlgorithmTag.objects.get_or_create(name=row['new_name'])

                for problem in old_tag.problems.all():
                    AlgorithmTagThrough.objects.get_or_create(
                        problem=problem, tag=new_tag
                    )
                    AlgorithmTagLocalization.objects.get_or_create(
                        algorithm_tag=new_tag,
                        language='EN',
                        full_name=row['full_name_EN'],
                    )
                    AlgorithmTagLocalization.objects.get_or_create(
                        algorithm_tag=new_tag,
                        language='PL',
                        full_name=row['full_name_PL'],
                    )
