import re

from django.conf import settings
from django.template import RequestContext
from django.template.loader import render_to_string

from oioioi.contests.processors import recent_contests
from oioioi.contests.utils import visible_contests
from oioioi.portals.widgets import register_widget
from oioioi.teachers.models import Teacher


class ContestSelectionWidget(object):
    name = 'contest_selection'
    compiled_tag_regex = re.compile(r'\[\[ContestSelection\]\]')
    TO_SHOW = getattr(settings, 'NUM_RECENT_CONTESTS', 5)

    def render(self, request, m):
        rcontests = recent_contests(request)
        contests = list(visible_contests(request).difference(rcontests))
        contests.sort(key=lambda x: x.creation_date, reverse=True)
        contests = (rcontests + contests)[:self.TO_SHOW+1]

        default_contest = None
        if rcontests:
            default_contest = rcontests[0]
        elif contests:
            default_contest = contests[0]

        context = {
            'contests': contests[:self.TO_SHOW],
            'default_contest': default_contest,
            'more_contests': len(contests) > self.TO_SHOW,
            'is_teacher': request.user.has_perm('teachers.teacher'),
            'is_inactive_teacher':
            request.user.is_authenticated() and
            bool(Teacher.objects.filter(user=request.user, is_active=False))
        }
        return render_to_string('teachers/widgets/contest-selection.html',
                                RequestContext(request, context))
register_widget(ContestSelectionWidget())
