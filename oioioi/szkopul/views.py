import django
from django.conf import settings
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.main_page import register_main_page_view
from oioioi.contests.controllers import submission_template_context
from oioioi.contests.models import Submission
from oioioi.contests.processors import recent_contests
from oioioi.contests.utils import visible_contests
from oioioi.problems.utils import filter_my_all_visible_submissions
from oioioi.szkopul.menu import navbar_links_registry

navbar_links_registry.register(
    name='contests_list',
    text=_("Contests"),
    url_generator=lambda request: reverse('select_contest'),
    order=100,
)

navbar_links_registry.register(
    name='problemset',
    text=_("Problemset"),
    url_generator=lambda request: reverse('problemset_main'),
    order=200,
)

navbar_links_registry.register(
    name='task_archive',
    text=_("Task archive"),
    url_generator=lambda request: reverse('task_archive'),
    order=300,
)

# TODO Add Portals main page to the menu:
# navbar_links_registry.register(
#     name='portals',
#     text=_("Portals"),
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
        queryset = Submission.objects.filter(user=request.user).order_by('-date')

        # current_contest = request.contest
        #
        # for s in queryset:
        #     request.contest = "lakdnasdn"#s.problem_instance.contest
        #     submissions.append(submission_template_context(request, s))
        #
        # request.contest = current_contest

        to_show = getattr(settings, 'NUM_PANEL_SUBMISSIONS', 7)

        # limit queryset size, because filtering all submissions is slow
        queryset = queryset[:to_show]
        limit_queryset_ids = [submission.id for submission in queryset]
        queryset = Submission.objects.filter(id__in=limit_queryset_ids).select_related(
            'user',
            'problem_instance',
            'problem_instance__contest',
            'problem_instance__round',
            'problem_instance__problem',
        )

        submissions_list = filter_my_all_visible_submissions(request, queryset)

        if django.VERSION >= (1, 11):
            submissions_list = submissions_list.order_by('-date')
        else:
            submissions_list.sort(reverse=True, key=lambda s: s.date)

        submissions = [
            submission_template_context(request, s) for s in submissions_list
        ]

        show_scores = any(s['can_see_score'] for s in submissions)

    context = {
        'navbar_links': navbar_links,
        'contests': contests,
        'submissions': submissions,
        'show_scores': show_scores,
    }

    return TemplateResponse(request, 'main-page.html', context)
