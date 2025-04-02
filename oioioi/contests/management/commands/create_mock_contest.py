from __future__ import print_function

import random
import re

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
    OriginInfoValue,
    OriginInfoValueLocalization,
    ProblemSite,
)

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

        levels = [1, 3, 3, 3]
        problems_per_leaf = 3
        problems = []

        ot_name = get_unique_field_value(OriginTag, 'name', 'olympiad')
        ot = OriginTag(name=ot_name)
        ot.save()
        
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
                    p = Problem()
                    p.save()
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
