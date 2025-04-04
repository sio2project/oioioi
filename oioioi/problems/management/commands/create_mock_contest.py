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
WORDS = ['Past', 'True', 'Whether', 'Claim', 'Reach', 'Class', 'Wish', 'Fight', 'Future', 'To', 'Prepare', 'System', 'Listen', 'End', 'Now', 'Dream', 'Section', 'Series', 'Appear', 'Rate', 'Bring', 'Man', 'Parent', 'Share', 'Create', 'Game', 'Weight', 'Imagine', 'However', 'Worry', 'Foot', 'Through', 'Tough', 'Number', 'Free', 'Police', 'Poor', 'Company', 'Heavy', 'Whether', 'Each', 'Run', 'Himself', 'Eight', 'Child', 'Life', 'Site', 'Sound', 'Against', 'Four', 'During', 'Key', 'Ball', 'Away', 'Form', 'Voice', 'Year', 'Really', 'Movie', 'May', 'Person', 'Central', 'Really', 'Many', 'Control', 'Article', 'Eight', 'Mean', 'Less', 'Fast', 'Lot', 'Day', 'Join', 'Movie', 'Partner', 'Popular', 'Book', 'Half', 'They', 'Such', 'Manage', 'Writer', 'Occur', 'Exist', 'Risk', 'Avoid', 'Change', 'Type', 'Main', 'Rather', 'Drug', 'Too', 'Lose', 'Why', 'Six', 'Old', 'Defense', 'Blue', 'Open', 'Large', 'Event', 'How', 'Street', 'Line', 'Forget', 'While', 'Off', 'Top', 'Back', 'Score', 'Record', 'Travel', 'House', 'Public', 'Among', 'Throw', 'Huge', 'Ball', 'Race', 'Both', 'Parent', 'Himself', 'Dream', 'Change', 'Bed', 'Miss', 'As', 'Oil', 'Chair', 'Mission', 'Piece', 'Foreign', 'Again', 'Be', 'Deep', 'Huge', 'Bit', 'Beyond', 'Cause', 'Really', 'Country', 'Truth', 'Do', 'Bar', 'Note', 'Mother', 'Read', 'Smile', 'Care', 'Agree', 'Decide', 'Section', 'Add', 'Result', 'Side', 'Tree', 'Chair', 'Forget', 'Series', 'A', 'Station', 'Threat', 'Carry', 'Their', 'Old', 'Street', 'Wife', 'Down', 'None', 'Scene', 'Only', 'Career', 'Grow', 'Drive', 'Such', 'Really', 'His', 'All', 'Trouble', 'Arm', 'Edge', 'School', 'College', 'Model', 'Radio', 'Manager', 'Law', 'Measure', 'Food', 'Sign', 'Up', 'New', 'Simple', 'Full', 'Visit', 'Federal', 'Beat', 'For', 'Not', 'Cause', 'Out', 'Four', 'Though', 'Stuff', 'Want', 'Those', 'Toward', 'Picture', 'Claim', 'Against', 'Letter', 'Gas', 'Late', 'Only', 'Mouth', 'Network', 'Fear', 'Role', 'Up', 'Produce', 'Throw', 'Couple', 'Yet', 'Trial', 'West', 'Toward', 'Much', 'Lead', 'Scene', 'Within', 'Them', 'Protect', 'Head', 'Front', 'West', 'Manage', 'Federal', 'Own', 'Drive', 'Bad', 'Whether', 'Truth', 'Police', 'Itself', 'Stage', 'Near', 'Today', 'Worker', 'Despite', 'Suffer', 'Decide', 'Never', 'Old', 'Require', 'Wonder', 'This', 'Turn', 'Blood', 'Exist', 'Allow', 'Suggest', 'Their', 'Quality', 'Stuff', 'Fact', 'Play', 'Sign', 'Whether', 'Design', 'Attack', 'Respond', 'Body', 'Test', 'Across', 'Growth', 'Friend', 'Almost', 'Under', 'Serve', 'Your', 'Body', 'Tree', 'Mother', 'Board', 'Truth', 'Reduce', 'Partner', 'Market', 'I', 'New', 'Total', 'Make', 'Natural', 'Fast', 'Call', 'Team', 'Firm', 'Close', 'Police', 'Word']

class Command(BaseCommand):
    help = _(
        "Create a mock contest with a lot of mock problems, useful for profiling"
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

        levels = [1, 50, 3, 3]
        problems_per_leaf = 3
        problems = []

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
