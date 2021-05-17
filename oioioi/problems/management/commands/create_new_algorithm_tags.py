import csv
import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import ugettext as _
from oioioi.problems.models import (
    AlgorithmTag,
    AlgorithmTagLocalization,
    AlgorithmTagThrough,
)


class Command(BaseCommand):
    help = _(
        "Delete all existing algorithm tags if delete flag specified. "
        "Create new algorithm tags based on the provided file.\n"
        "Usage: manage.py create_new_algorithm_tags -f|--file <filename> "
        "[-d|--delete] [-dr|--dry_run]"
    )

    def add_arguments(self, parser):
        parser.add_argument('-f', '--file', type=str)
        parser.add_argument('-d', '--delete', action='store_true')
        parser.add_argument('-dr', '--dry_run', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        filename = options.get('file', '')
        delete = options.get('delete')
        dry_run = options.get('dry_run')

        if not filename:
            raise CommandError(_("Filename is obligatory."))

        if not os.path.exists(filename):
            raise CommandError(_("File not found: ") + filename)

        if delete:
            if dry_run:
                for tag in AlgorithmTag.objects.all():
                    print('Algorithm tag %s:' % tag)
                    for tag_local in AlgorithmTagLocalization.objects.filter(algorithm_tag=tag):
                        print('Delete algorithm tag localization: %s' % tag_local)
                    for tag_through in AlgorithmTagThrough.objects.filter(tag=tag):
                        print('Delete algorithm tag through: %s, %s' % tag_through, tag_through.problem)
                    print('Delete algorithm tag: %s' % tag)
            else:
                AlgorithmTag.objects.all().delete()

        with open(filename, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for row in csv_reader:
                if dry_run:
                    print('Create algorithm tag: %s' % row['name'])
                    print('Create algorithm tag localization: %s' % row['full_name_pl'])
                    print('Create algorithm tag localization: %s' % row['full_name_en'])
                else:
                    new_tag, _ = AlgorithmTag.objects.get_or_create(name=row['name'])
                    AlgorithmTagLocalization.objects.get_or_create(
                        algorithm_tag=new_tag,
                        language='pl',
                        full_name=row['full_name_pl'],
                    )
                    AlgorithmTagLocalization.objects.get_or_create(
                        algorithm_tag=new_tag,
                        language='en',
                        full_name=row['full_name_en'],
                    )
