import csv
import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import ugettext as _
from oioioi.problems.models import (
    OriginInfoCategory,
    OriginInfoCategoryLocalization,
    OriginInfoValue,
    OriginInfoValueLocalization,
    OriginTag,
    OriginTagLocalization,
    Tag,
)


class Command(BaseCommand):
    help = _("Migrates old tags to new origin tags.")

    def add_arguments(self, parser):
        parser.add_argument('-f', '--file', type=str)

    @transaction.atomic
    def handle(self, *args, **options):
        filename = options.get('file', '')

        if not filename:
            raise CommandError(_("Filename is obligatory."))

        if not os.path.exists(filename):
            raise CommandError(_("File not found: ") + filename)

        eng_tag = Tag.objects.get(name='eng')

        with open(filename, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for row in csv_reader:
                origin_tag, _ = OriginTag.objects.get_or_create(
                    name=row['OriginTag_name']
                )
                OriginTagLocalization.objects.get_or_create(
                    origin_tag=origin_tag,
                    language='en',
                    full_name=row['OriginTagLocalization_full_name_EN'],
                    short_name=row['OriginTagLocalization_short_name_EN'],
                )
                OriginTagLocalization.objects.get_or_create(
                    origin_tag=origin_tag,
                    language='pl',
                    full_name=row['OriginTagLocalization_full_name_PL'],
                    short_name=row['OriginTagLocalization_short_name_PL'],
                )

                origin_info_category, _ = OriginInfoCategory.objects.get_or_create(
                    parent_tag=origin_tag,
                    name=row['OriginInfoCategory_name'],
                    order=row['OriginInfoCategory_order'],
                )
                OriginInfoCategoryLocalization.objects.get_or_create(
                    origin_info_category=origin_info_category,
                    language='en',
                    full_name=row['OriginInfoCategoryLocalization_full_name_EN'],
                )
                OriginInfoCategoryLocalization.objects.get_or_create(
                    origin_info_category=origin_info_category,
                    language='pl',
                    full_name=row['OriginInfoCategoryLocalization_full_name_PL'],
                )

                origin_info_value, _ = OriginInfoValue.objects.get_or_create(
                    parent_tag=origin_tag,
                    category=origin_info_category,
                    value=row['OriginInfoValue_value'],
                    order=row['OriginInfoValue_order'],
                )
                OriginInfoValueLocalization.objects.get_or_create(
                    origin_info_value=origin_info_value,
                    language='en',
                    full_value=row['OriginInfoValueLocalization_full_value_EN'],
                )
                OriginInfoValueLocalization.objects.get_or_create(
                    origin_info_value=origin_info_value,
                    language='pl',
                    full_value=row['OriginInfoValueLocalization_full_value_PL'],
                )

                old_tag = Tag.objects.get(name=row['Tag_name'])
                for problem in old_tag.problems.all():
                    # Add a new origin tag only to problems without the 'eng'
                    # legacy tag.
                    if not problem in eng_tag.problems.all():
                        origin_tag.problems.add(problem)
                        origin_info_value.problems.add(problem)
