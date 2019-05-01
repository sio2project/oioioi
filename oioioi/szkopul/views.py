from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from oioioi.base.main_page import register_main_page_view
from oioioi.szkopul.menu import navbar_links_registry
from oioioi.contests.utils import visible_contests
from oioioi.contests.controllers import submission_template_context
from oioioi.contests.models import Submission
from oioioi.contests.processors import recent_contests

navbar_links_registry.register(
    name='contests_list',
    text=_('Contests'),
    url_generator=lambda request: reverse('select_contest'),
    order=100,
)

navbar_links_registry.register(
    name='problemset',
    text=_('Problemset'),
    url_generator=lambda request: reverse('problemset_main'),
    order=200,
)

navbar_links_registry.register(
    name='task_archive',
    text=_('Task archive'),
    # TODO Change the following URL when the Task Archive
    #      gets moved from the global portal on Szkopul.
    url_generator=lambda request:
        'https://szkopul.edu.pl/portal/problemset' +
        ('_eng' if request.LANGUAGE_CODE != 'pl' else ''),
    order=300,
)

# TODO Add Portals main page to the menu:
# navbar_links_registry.register(
#     name='portals',
#     text=_('Portals'),
#     ...
# )

@register_main_page_view(order=100)
def main_page_view(request):
    navbar_links = navbar_links_registry.template_context(request)

    to_show = getattr(settings, 'NUM_RECENT_CONTESTS', 7)
    rcontests = recent_contests(request)
    contests = list(visible_contests(request).difference(rcontests))
    contests.sort(key=lambda x: x.creation_date, reverse=True)
    contests = (rcontests + contests)[:to_show]

    submissions = []
    show_scores = False
    if request.user.is_authenticated:
        queryset = Submission.objects \
            .filter(user=request.user) \
            .order_by('-date') \
            .select_related('user', 'problem_instance',
                            'problem_instance__contest',
                            'problem_instance__round',
                            'problem_instance__problem')

        # current_contest = request.contest
        #
        # for s in queryset:
        #     request.contest = "lakdnasdn"#s.problem_instance.contest
        #     submissions.append(submission_template_context(request, s))
        #
        # request.contest = current_contest

        submissions = [submission_template_context(request, s) for s in queryset]

        to_show = getattr(settings, 'NUM_PANEL_SUBMISSIONS', 7)
        submissions = submissions[:to_show]
        show_scores = any(s['can_see_score'] for s in submissions)

    context = {
        'navbar_links': navbar_links,
        'contests': contests,
        'submissions': submissions,
        'show_scores': show_scores,
    }

    return TemplateResponse(request, 'main-page.html', context)
