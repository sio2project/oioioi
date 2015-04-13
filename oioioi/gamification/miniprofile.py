from django.db.models import F
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from oioioi.base.menu import OrderedRegistry
from oioioi.gamification.friends import UserFriends
from oioioi.contests.models import UserResultForProblem


MAX_SUGGESTIONS_FROM_FRIENDS = 10

miniprofile_row_registry = OrderedRegistry()
miniprofile_tab_registry = OrderedRegistry()


"""Adds a row to the miniprofile given a view function. The view
   should return a string.

   Warning: Miniprofile is added to the site through a context processor,
   so the use of RequestContext in miniprofile tabs is impossible.
"""
miniprofile_row = miniprofile_row_registry.register_decorator


def miniprofile_tab(title, order):
    """Adds a tab to the miniprofile given heading and view function. The view
       should return a string.

       Warning: Miniprofile is added to the site through a context processor,
       so the use of RequestContext in miniprofile tabs is impossible.
    """
    def decorator(func):
        miniprofile_tab_registry.register((title, func), order)
        return func
    return decorator


@miniprofile_row(0)
def user_info_row(request):
    return render_to_string('gamification/miniprofile/user-info.html',
        {'user': request.user})


@miniprofile_row(100)
def tabs_row(request):
    """Renders miniprofile tabs into one row."""
    tabs_with_ids = [(i, title, view(request))
            for i, (title, view) in enumerate(miniprofile_tab_registry)]

    return render_to_string('gamification/miniprofile/tabs.html',
            {'tabs': tabs_with_ids})


@miniprofile_tab(_("Friends"), 100)
def friends_tab(request):
    return render_to_string('gamification/miniprofile/tabs/friends.html',
            {'friends': UserFriends(request.user)
                .friends.order_by('username')})


@miniprofile_tab(_("Problems"), 200)
def friend_problems_tab(request):
    friends = UserFriends(request.user).friends

    rfps = UserResultForProblem.objects.filter(
        user__in=friends,
        submission_report__scorereport__score=
        F('submission_report__scorereport__max_score'),
        submission_report__submission__problem_instance__contest__isnull=True
    ).select_related('submission_report__submission'
                     '__problem_instance__problem')

    submissions = [rfp.submission_report.submission
                   for rfp in rfps[:MAX_SUGGESTIONS_FROM_FRIENDS]]

    return render_to_string('gamification/miniprofile/tabs/problems.html',
            {'submissions': submissions})
