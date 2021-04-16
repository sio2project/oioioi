import csv
import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import ugettext as _
from oioioi.problems.models import Tag, TagThrough, ProblemStatement


class Command(BaseCommand):
    help = _("Copies problem statements to problems with origin tags already added.")

    def add_arguments(self, parser):
        parser.add_argument('-f', '--file', type=str)

    @transaction.atomic
    def handle(self, *args, **options):
        filename = options.get('file', '')

        if not filename:
            raise CommandError(_("Filename is obligatory."))

        if not os.path.exists(filename):
            raise CommandError(_("File not found: ") + filename)

        tag_eng = Tag.objects.get(name='eng')

        with open(filename, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for row in csv_reader:
                old_tag = Tag.objects.get(name=row['Tag_name'])
                for problem in old_tag.problems.all():
                    has_tag_eng = problem in tag_eng.problems.all()
                    no_origin_version = row['language_version_with_no_origin']

                    if (has_tag_eng and no_origin_version == 'en') or (
                        (not has_tag_eng) and no_origin_version == 'pl'
                    ):
                        # Firstly, make sure there is a single problem statement
                        # for the current problem.
                        problem_statements = ProblemStatement.objects.filter(
                            problem=problem
                        )
                        if problem_statements.count() != 1:
                            print(
                                '%s: there is no single statement ' % problem
                                + 'for this problem'
                            )
                        else:
                            # Secondly, make sure there is a single problem
                            # with origin tag added for the current problem.
                            problems_with_origin = (
                                old_tag.problems.all()
                                .filter(short_name=problem.short_name)
                                .exclude(name=problem.name)
                            )
                            if problems_with_origin.count() != 1:
                                print(
                                    '%s: there is no single problem ' % problem
                                    + 'with origin tag added for this problem'
                                )
                            else:
                                # Thirdly, make sure there is a single problem
                                # statement for the problem with origin tag added.
                                problem_with_origin = problems_with_origin.get()
                                problem_with_origin_statements = (
                                    ProblemStatement.objects.filter(
                                        problem=problem_with_origin
                                    )
                                )
                                if problem_with_origin_statements.count() != 1:
                                    print(
                                        '%s: there is no ' % problem_with_origin
                                        + 'single statement for this problem'
                                    )
                                else:
                                    # Only if all three conditions were satisfied
                                    # it is possible to copy the problem statement
                                    # without any ambiguity.
                                    problem_statement_copy = problem_statements.get()
                                    problem_statement_copy.problem = problem_with_origin
                                    problem_statement_copy.pk = None
                                    problem_statement_copy.save()

                                    # Add a special tag to mark problems with problem
                                    # statements copied.
                                    tag_copied, _ = Tag.objects.get_or_create(
                                        name='copied'
                                    )
                                    TagThrough.objects.get_or_create(
                                        problem=problem,
                                        tag=tag_copied,
                                    )
