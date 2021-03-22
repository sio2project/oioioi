import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import ugettext as _
from oioioi.problems.models import AlgorithmTag, AlgorithmTagThrough, OriginTag, Tag


def _migrate_tags(old_tags_filename, tags_manager, relationship_manager=None):
    with open(old_tags_filename, 'r') as old_tags_file:
        for line in old_tags_file:
            old_tag_name, new_tag_name = line.split()
            old_tag = Tag.objects.get(name=old_tag_name)
            new_tag, _ = tags_manager.get_or_create(name=new_tag_name)

            for problem in old_tag.problems.all():
                if problem not in new_tag.problems.all():
                    if relationship_manager:
                        relationship_manager.create(problem=problem, tag=new_tag)
                    else:
                        new_tag.problems.add(problem)


class Command(BaseCommand):
    help = _("Migrates old tags to new origin or algorithm tags.")

    def add_arguments(self, parser):
        parser.add_argument('-o', '--old_origin_tags_filename', type=str)
        parser.add_argument('-a', '--old_algorithm_tags_filename', type=str)

    @transaction.atomic
    def handle(self, *args, **options):
        old_origin_tags_filename = options.get('old_origin_tags_filename', '')
        old_algorithm_tags_filename = options.get('old_algorithm_tags_filename', '')

        if not (old_origin_tags_filename or old_algorithm_tags_filename):
            raise CommandError(_("At least one file should be given."))

        if old_origin_tags_filename and not os.path.exists(old_origin_tags_filename):
            raise CommandError(_("File not found: ") + old_origin_tags_filename)

        if old_algorithm_tags_filename and not os.path.exists(
            old_algorithm_tags_filename
        ):
            raise CommandError(_("File not found: ") + old_algorithm_tags_filename)

        if old_origin_tags_filename:
            _migrate_tags(old_origin_tags_filename, OriginTag.objects)

        if old_algorithm_tags_filename:
            _migrate_tags(
                old_algorithm_tags_filename,
                AlgorithmTag.objects,
                relationship_manager=AlgorithmTagThrough.objects,
            )
