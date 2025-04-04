from __future__ import print_function

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

class Command(BaseCommand):
    help = _(
        "Create a mock competition with empty mock problems. "
        "Useful for replicating the size of the production databse in the local environment. "
        "This can be used for finding performance bottlenecks, "
        "where the number of queries grows with the number of problems in the database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-b",
            "--branches",
            type=int,
            action="store",
            dest="branches",
            help="Number of top-level branches of the competition tree. Conceptually, this is the number of stages of the competition."
        )

        parser.add_argument(
            "-n",
            "--name",
            type=str,
            action="store",
            dest="competition_name",
            help="Name of the mock competition which will be created."
        )

        parser.add_argument(
            "-l",
            "--levels",
            type=int,
            action="store",
            dest="levels",
            help="Number of levels of nesting of the competition."
        )

    @transaction.atomic
    def handle(self, *args, **options):
        def get_unique_field_value(model_class, field_name, base_value):
            regex_pattern = base_value + r"(\d+)"

            filter_kwargs = {f"{field_name}__regex": f"^{regex_pattern}"}

            existing_vals = model_class.objects.filter(**filter_kwargs).values_list(field_name, flat=True)

            unused = 0
            for value in existing_vals:
                num = int(re.search(regex_pattern, value).group(1))
                unused = max(unused, num + 1)

            return base_value + str(unused)

        levels = [1]
        levels.append(options['branches'])
        levels += [3] * (options['levels'] - 1)
        problems_per_leaf = 3
        problems = []

        ot_name = None

        if options['competition_name'] is not None:
            ot_name = options['competition_name']
            if OriginTag.objects.filter(name=ot_name).exists():
                raise Exception(
                    "An origin_tag with competition name '%s' already exists, " \
                    "choose a non-duplicate name for the competition." % ot_name
                )
        else:
            ot_name = get_unique_field_value(OriginTag, 'name', 'olympiad')

        ot = OriginTag(name=ot_name)
        ot.save()

        OriginTagLocalization(
            origin_tag = ot,
            language = get_language(),
            short_name = ot_name,
            full_name = ot_name
        ).save()
        
        oics = []
        oivs = []
        oiv_count = 1
        for i in range(len(levels)):
            oic = OriginInfoCategory(parent_tag=ot, name = 'level%d' % i, order = i)
            oic.save()
            oics += [oic]
            oivs += [[]]
            oiv_count *= levels[i]
            for j in range(oiv_count):
                oiv = OriginInfoValue(
                    value = '%d_%d' % (i, j),
                    parent_tag = ot,
                    category = oics[i],
                )
                oiv.save()
                oivs[i].append(oiv)

                localization = OriginInfoValueLocalization(
                    origin_info_value = oiv,
                    language = get_language(),
                    full_value = 'Level %d - %d' % (i, j)
                )
                localization.save()

        def f(i, name):
            if i == len(levels):
                problems = []
                for i in range(problems_per_leaf):
                    # This is at most 29, so barely below the model limit of 30 chars
                    words = [random.choice(WORDS), random.choice(WORDS)]
                    problem_name = 'Problem %s %s %s' % (words[0], words[1], ''.join(random.choices(string.digits, k=6)))
                    p = Problem(
                        short_name = words[0].lower()
                    )
                    name = ProblemName(
                        problem = p,
                        language = get_language(),
                        name = problem_name
                    )
                    p.save()
                    name.save()
                    # Use a random ID large enough, that the Birthday Paradox won't be a problem
                    ProblemSite(problem = p, url_key = str(random.randrange(2 ** 40))).save()
                    ot.problems.add(p)
                    problems += [p]
                return problems
            else:
                problems = []
                for j in range(levels[i]):
                    subname = '%s_%d' % (name, j)
                    subproblems = f(i+1, subname)
                    oiv = oivs[i][j]
                    problems += subproblems
                    for p in subproblems:
                        oiv.problems.add(p)
                return problems

        probs = f(0, '')
