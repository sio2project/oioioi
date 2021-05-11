import csv
import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import ugettext as _
from oioioi.problems.models import ProblemStatement, Tag, TagThrough


def _get_problem_statements(problem, multiple):
    problem_statements_query = ProblemStatement.objects.filter(problem=problem)
    problem_statements = problem_statements_query
    if problem_statements.count() != 1 and multiple:
        problem_statements = [
            problem_statement
            for problem_statement in problem_statements
            if str(problem_statement.content).endswith('.html')
            and not problem_statement.language
        ]
        excluded_with_language = any(
            problem_statement
            for problem_statement in problem_statements_query
            if problem_statement.language
            and not problem_statement in problem_statements
        )
        if excluded_with_language:
            print(
                '%s: has more than one problem statement ' % problem
                + 'and at least one of them has added a language'
            )
            problem_statements = []

    return [problem_statement for problem_statement in problem_statements]


class Command(BaseCommand):
    help = _("Copies problem statements to problems with origin tags already added.")

    def add_arguments(self, parser):
        parser.add_argument('-f', '--file', type=str)
        parser.add_argument('-m', '--multiple', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        filename = options.get('file', '')
        multiple = options.get('multiple')

        if not filename:
            raise CommandError(_("Filename is obligatory."))

        if not os.path.exists(filename):
            raise CommandError(_("File not found: ") + filename)

        tag_eng = Tag.objects.get(name='eng')
        tag_copied, _ = Tag.objects.get_or_create(name='copied')

        with open(filename, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for row in csv_reader:
                old_tag = Tag.objects.get(name=row['Tag_name'])
                for problem in old_tag.problems.all():
                    has_tag_eng = problem in tag_eng.problems.all()
                    no_origin_version = row['language_version_with_no_origin']
                    has_tag_copied = TagThrough.objects.filter(
                        problem=problem, tag=tag_copied
                    ).exists()

                    if not has_tag_copied and (
                        (has_tag_eng and no_origin_version == 'en')
                        or ((not has_tag_eng) and no_origin_version == 'pl')
                    ):
                        # Firstly, make sure there is a single problem statement
                        # for the current problem.
                        problem_statements = _get_problem_statements(problem, multiple)
                        if len(problem_statements) != 1:
                            print(
                                '%s: there is no single statement ' % problem
                                + 'for the current problem'
                            )
                        else:
                            # Secondly, make sure there is a single problem
                            # with origin tag added for the current problem.
                            problems_with_origin = (
                                old_tag.problems.all()
                                .filter(short_name=problem.short_name)
                                .exclude(legacy_name=problem.legacy_name)
                            )
                            if problems_with_origin.count() != 1:
                                print(
                                    '%s: there is no single problem ' % problem
                                    + 'with origin tag added for the current problem'
                                )
                            else:
                                # Thirdly, make sure there is a single problem
                                # statement for the problem with origin tag added.
                                problem_with_origin = problems_with_origin.get()
                                problem_with_origin_statements = (
                                    _get_problem_statements(
                                        problem_with_origin, multiple
                                    )
                                )
                                if len(problem_with_origin_statements) != 1:
                                    print(
                                        '%s: there is no ' % problem_with_origin
                                        + 'single statement for that problem'
                                    )
                                else:
                                    # Only if all three conditions were not satisfied
                                    # it is possible to copy the problem statement
                                    # without any ambiguity.
                                    problem_with_origin_statement = (
                                        problem_with_origin_statements[0]
                                    )

                                    problem_statement_copy = problem_statements[0]
                                    problem_statement_copy.problem = problem_with_origin
                                    problem_statement_copy.pk = None

                                    if no_origin_version == 'en':
                                        problem_with_origin_statement.language = 'pl'
                                        problem_statement_copy.language = 'en'
                                    else:
                                        problem_with_origin_statement.language = 'en'
                                        problem_statement_copy.language = 'pl'

                                    problem_with_origin_statement.save()
                                    problem_statement_copy.save()

                                    # Add a special tag to mark problems with problem
                                    # statements copied.
                                    TagThrough.objects.get_or_create(
                                        problem=problem,
                                        tag=tag_copied,
                                    )
