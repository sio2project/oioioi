import random
import re
import string

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db import transaction
from django.utils.translation import gettext as _
from django.utils.translation import get_language

from functools import *

from oioioi.problems.models import (
    Problem,
    OriginInfoCategory,
    OriginTag,
    OriginTagLocalization,
    OriginInfoValue,
    OriginInfoValueLocalization,
    ProblemSite,
    ProblemName,
)

# List of 300 random words of length at most 6
# Used for creating problems with "believable" names
WORDS = ['Whole', 'Crime', 'Eight', 'Member', 'Join', 'Man', 'Thing', 'Box', 'Friend', 'Piece', 'Good', 'Eat', 'Only', 'Save', 'About', 'Six', 'Cup', 'Yeah', 'Reveal', 'Whose', 'Remain', 'Speak', 'Card', 'Entire', 'Key', 'When', 'Sense', 'Drive', 'Where', 'Little', 'Need', 'Can', 'Bit', 'Never', 'Coach', 'Push', 'Where', 'Small', 'Remain', 'Future', 'Which', 'Around', 'Score', 'Born', 'Score', 'Remain', 'Thing', 'Tend', 'Bit', 'Tree', 'Type', 'Say', 'Two', 'Kind', 'Half', 'Truth', 'Occur', 'Wish', 'Big', 'Glass', 'Just', 'Hear', 'Lose', 'His', 'Entire', 'List', 'Year', 'Type', 'Cost', 'Bank', 'Hair', 'Try', 'Color', 'Choice', 'Former', 'Enough', 'Task', 'Fast', 'Little', 'Smile', 'Floor', 'Only', 'Fly', 'Never', 'Energy', 'Rise', 'Or', 'Recent', 'Place', 'Share', 'Book', 'Soon', 'Poor', 'Tend', 'Learn', 'Guess', 'Eat', 'Eye', 'Those', 'Full', 'Sing', 'Data', 'Me', 'Charge', 'Never', 'Grow', 'Job', 'These', 'Rock', 'Itself', 'Until', 'Seek', 'Yes', 'Soon', 'Break', 'Follow', 'Stuff', 'Good', 'Side', 'Sign', 'Either', 'Itself', 'Per', 'Spring', 'Ahead', 'Region', 'Power', 'Real', 'Wife', 'Radio', 'Walk', 'Doctor', 'Event', 'Sort', 'Film', 'Form', 'Under', 'Fast', 'Range', 'Mrs', 'Bring', 'Ago', 'Matter', 'Oil', 'Change', 'A', 'Help', 'Baby', 'Whom', 'Own', 'Loss', 'Debate', 'Seek', 'Sport', 'Wife', 'Read', 'Court', 'Land', 'Reason', 'Wrong', 'Report', 'Garden', 'Use', 'Film', 'Avoid', 'Worker', 'Civil', 'Assume', 'Our', 'First', 'Color', 'Girl', 'Second', 'Year', 'Window', 'Past', 'Kind', 'Change', 'She', 'Within', 'Page', 'Action', 'Road', 'Leader', 'Late', 'Really', 'Here', 'Far', 'Minute', 'Sense', 'Coach', 'Play', 'Return', 'Quite', 'Author', 'Fill', 'Attack', 'Thing', 'Option', 'Choose', 'This', 'Bit', 'Should', 'Result', 'Rate', 'Dog', 'Push', 'Early', 'Upon', 'Data', 'For', 'Mother', 'Poor', 'Nor', 'Reason', 'Pretty', 'Take', 'Room', 'Live', 'Design', 'See', 'Center', 'Better', 'Unit', 'Thus', 'Town', 'Space', 'End', 'Act', 'Today', 'Weight', 'They', 'Young', 'Mr', 'Reason', 'Easy', 'Affect', 'Soon', 'Thing', 'Maybe', 'Learn', 'Often', 'Agree', 'Become', 'Lose', 'There', 'Rock', 'Heavy', 'Though', 'Space', 'Total', 'Base', 'Glass', 'Visit', 'Form', 'Team', 'Choice', 'Much', 'Behind', 'Room', 'Data', 'Family', 'Hour', 'North', 'Fly', 'Right', 'Remain', 'White', 'They', 'Report', 'There', 'Song', 'Focus', 'Cover', 'Within', 'Then', 'Board', 'Her', 'Yeah', 'Last', 'By', 'Change', 'Push', 'That', 'Will', 'About', 'Until', 'Fire', 'Apply', 'Big', 'Fish', 'Have', 'Choice', 'Fund', 'Radio', 'Upon', 'Around', 'There', 'Have', 'Apply']

# Helper command, which finds the the smallest natural number n, such that
# no object from the model model_class has a field equal to [base_value]n.
# This function is to be used for finding anyname that isn't
# used in the database yet.
def get_unique_field_value(model_class, field_name, base_value):

    filter_kwargs = {f"{field_name}__startswith": base_value}

    existing_vals = model_class.objects.filter(**filter_kwargs).values_list(field_name, flat=True)

    unused = 0
    regex_pattern = base_value + r"(\d+)"
    for value in existing_vals:
        # Try to convert to number
        try:
            # Find the integer after base_value in the field
            num = int(re.search(regex_pattern, value).group(1)) 
            # Make sure unused is different than num
            unused = max(unused, num + 1)
        except ValueError:
            pass

    return base_value + str(unused)

def create_origin_tag(competition_name):
    """Create an OriginTag for the competition_name with the name it is given or
    a unique name starting with 'mock'
    """
    if competition_name is not None:
        # Disallow duplicate origin tags, and raise an exception
        if OriginTag.objects.filter(name=competition_name).exists():
            raise Exception(
                "An origin_tag with competition name '%s' already exists, " \
                "choose a non-duplicate name for the competition." % competition_name
            )
    else:
        # Find a unique name of the form 'mock%d'
        competition_name = get_unique_field_value(OriginTag, 'name', 'mock')

    # Create top-level origin tag for the competition.
    origin_tag = OriginTag(name=competition_name)
    origin_tag.save()

    # Assign the name ot_name for the competiton for the default language.
    OriginTagLocalization(
        origin_tag = origin_tag,
        language = get_language(),
        short_name = competition_name,
        full_name = competition_name
    ).save()

    return origin_tag

def create_origin_info_categories(origin_tag, levels):
    """Create an OriginInfoCategory for each level described by levels
    """
    categories = []
    for level in range(len(levels)):
        category = OriginInfoCategory(parent_tag=origin_tag, name = 'level%d' % level, order = level)
        category.save()
        categories.append(category)

    return categories

def create_origin_info_values(origin_tag, levels, categories):
    """Create levels[level] values for each category
    """
    info_values = [[] for i in range(len(levels))]
    for level in range(len(levels)):
        for i in range(levels[level]):
            # Create an OriginInfoValue for each branch in the current level
            info_value = OriginInfoValue(
                value = '%d_%d' % (level, i),
                parent_tag = origin_tag,
                category = categories[level],
            )
            info_value.save()
            info_values[level].append(info_value)

            # Name the OriginInfoValue in the default language
            localization = OriginInfoValueLocalization(
                origin_info_value = info_value,
                language = get_language(),
                full_value = 'Level %d - %d' % (level, i)
            )
            localization.save()

    return info_values

class Command(BaseCommand):
    help = (
        "Create a mock competition with empty problems. "
        "Useful for replicating the size of the production databse in the local environment. "
        "This can be used for finding performance bottlenecks, "
        "where the number of queries grows with the number of problems in the database. "
        "WARNING: this operation will fill your database with a lot of rubbish data. "
        "Only use it if you're sure that's not a problem, or use 'python manage.py dumpdata' "
        "and 'python manage.py loaddata'."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-b",
            "--branches",
            type=int,
            action="store",
            dest="branches",
            required=True,
            default=10,
            help="Number of top-level branches of the competition tree. Conceptually, this is the number of stages of the competition."
        )

        parser.add_argument(
            "-n",
            "--name",
            type=str,
            action="store",
            dest="competition_name",
            help="Name of the mock competition which will be created. If a competition with this name already exists, an error will be thrown. " \
                "If not specified, the name will be 'mock{N}', where N is the smallest number, " \
                "such that no competition of with this name already exists."
        )

        parser.add_argument(
            "-l",
            "--levels",
            type=int,
            action="store",
            dest="levels",
            default=2,
            help="Number of levels of nesting of the competition."
        )

        parser.add_argument(
            "-s",
            "--seed",
            type=int,
            action="store",
            dest="seed",
            help="Random seed to use for problem name randomization."
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['seed'] is not None:
            random.seed(options['seed'])

        # Array of branching factors for each level of the tree of problems.
        levels = [1]
        levels.append(options['branches'])
        levels += [3] * (options['levels'] - 1)

        PROBLEMS_PER_LEAF = 3

        origin_tag = create_origin_tag(options['competition_name'])
        categories = create_origin_info_categories(origin_tag, levels)
        info_values = create_origin_info_values(origin_tag, levels, categories)

        # Recursive function for creating problem. It traverses the tree of 
        # problems depth-first and returns all the problems in its subtree.
        def recurse(level, name):
            problems = []

            if level == len(levels):
                # Reached bottom level - create problems
                for i in range(PROBLEMS_PER_LEAF):
                    words = [random.choice(WORDS), random.choice(WORDS)]
                    problem_name = 'Problem %s %s %s' % (words[0], words[1], ''.join(random.choices(string.digits, k=6)))
                    p = Problem(
                        # The short name will be the first word in lower case
                        short_name = words[0].lower()
                    )
                    problems.append(p)

                    name = ProblemName(
                        problem = p,
                        language = get_language(),
                        name = problem_name
                    )

                    p.save()
                    name.save()

                    # Assign an empty fake problem site for a problem.
                    # Use a random ID large enough, that the Birthday Paradox won't be a problem
                    ProblemSite(problem = p, url_key = str(random.randrange(2 ** 40))).save()

                    # Add the problem to the competition origin tag.
                    origin_tag.problems.add(p)
                return problems
            else:
                for i in range(levels[level]):
                    subname = '%s_%d' % (name, i)
                    # Recurse for each of levels[level] branches
                    subproblems = recurse(level+1, subname)

                    problems += subproblems

                    # Assign each of the subproblems in the current branch to the
                    # corresponding info_value
                    info_value = info_values[level][i]
                    for p in subproblems:
                        info_value.problems.add(p)

            return problems

        recurse(0, '')
