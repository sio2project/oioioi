import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import ugettext as _
from oioioi.problems.models import ProblemName, Tag


def _get_legacy_origin_tag(problem, legacy_origin_tags):
    for tag in problem.tag_set.all():
        if tag.name in legacy_origin_tags:
            return tag
    return None


class Command(BaseCommand):
    help = _(
        "Searches for repeated problems in different languages and adds "
        "translations of their names to both of them. Every repeated problem "
        "has exactly one legacy origin tag."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '-f',
            '--file',
            type=str,
            help=_("File with all possible legacy origin tags, separated with commas."),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        filename = options.get('file', '')

        if not filename:
            raise CommandError(_("Filename is obligatory."))

        if not os.path.exists(filename):
            raise CommandError(_("File not found: ") + filename)

        with open(filename, mode='r') as tags_file:
            legacy_origin_tags = set(tags_file.read().split(','))

        tag_eng = Tag.objects.get(name='eng')
        for problem_en in tag_eng.problems.all():
            legacy_origin_tag = _get_legacy_origin_tag(problem_en, legacy_origin_tags)
            if legacy_origin_tag:
                problems_pl = (
                    legacy_origin_tag.problems.all()
                    .filter(short_name=problem_en.short_name)
                    .exclude(legacy_name=problem_en.legacy_name)
                )
                if problems_pl.count() != 1:
                    print(
                        "%s: there is no single problem " % problem_en
                        + "with the same short name and the same legacy origin tag."
                    )
                else:
                    problem_pl = problems_pl.get()
                    name_language_pairs = [
                        (problem_en.legacy_name, 'en'),
                        (problem_pl.legacy_name, 'pl'),
                    ]
                    for name, language in name_language_pairs:
                        for problem in (problem_en, problem_pl):
                            ProblemName.objects.get_or_create(
                                problem=problem, name=name, language=language
                            )
