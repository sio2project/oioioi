from __future__ import print_function

import random

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db import transaction
from django.utils.translation import gettext as _

from functools import *

from oioioi.problems.models import (
    Problem,
    OriginInfoCategory,
    OriginTag,
    OriginInfoValue,
    ProblemSite,
)

class Command(BaseCommand):
    help = _(
        "Create a mock contest with a lot of mock problems, useful for profiling"
    )

    @transaction.atomic
    def handle(self, *args, **options):
        levels = [1, 50, 3, 3]
        problems_per_leaf = 3
        problems = []
        ot = OriginTag(name="olympiad7")
        ot.save()
        
        oics = []
        for i in range(len(levels)):
            oic = OriginInfoCategory(parent_tag=ot, name = 'level%d' % i, order = i)
            oic.save()
            oics += [oic]

        def f(i, name):
            if i == len(levels):
                problems = []
                for i in range(problems_per_leaf):
                    p = Problem()
                    p.save()
                    ProblemSite(problem = p, url_key = str(random.randrange(2 ** 40))).save()
                    ot.problems.add(p)
                    problems += [p]
                return problems
            else:
                problems = []
                for j in range(levels[i]):
                    subname = '%s_%d' % (name, j)
                    subproblems = f(i+1, subname)
                    problems += subproblems
                    print(name, subname, i)
                    oiv = OriginInfoValue(
                        value = subname,
                        parent_tag = ot,
                        category = oics[i],
                    )
                    oiv.save()
                    for p in subproblems:
                        oiv.problems.add(p)
                    oiv.save()
                return problems

        probs = f(0, '')
        print(OriginTag.objects.all())
        print(OriginInfoCategory.objects.all())
        print(OriginInfoValue.objects.all())
