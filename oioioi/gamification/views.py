from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_GET, require_POST
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.http import JsonResponse

from oioioi.base.menu import account_menu_registry
from oioioi.base.utils import jsonify
from oioioi.gamification.controllers import CodeSharingController
from oioioi.gamification.experience import Experience
from oioioi.gamification.friends import UserFriends
from oioioi.gamification.profile import profile_registry
from oioioi.gamification.models import ProblemDifficulty
from oioioi.problems.problem_site import problem_site_tab

# pylint: disable=W0611
import oioioi.gamification.handlers
import oioioi.gamification.widgets


@jsonify
@require_GET
def check_user_exists_view(request):
    if 'username' in request.GET:
        username = request.GET['username']
        if User.objects.filter(username=username).exists():
            url = reverse('view_profile', args=[username])
            return {'userExists': True, 'profileUrl': url}

    return {'userExists': False}


@account_menu_registry.register_decorator(_("Profile"),
    lambda request: reverse('view_current_profile'), order=50)
@login_required
def profile_view(request, username=None):
    shown_user = None

    if username is None:
        shown_user = request.user
    else:
        shown_user = get_object_or_404(User.objects, username=username)

    exp = Experience(shown_user)
    friends = UserFriends(request.user)
    is_friend = friends.is_friends_with(shown_user)
    pending_incoming_friendship_request = friends.has_request_from(shown_user)
    sent_friendship_request = friends.sent_request_to(shown_user)

    has_portal = False
    if 'oioioi.portals' in settings.INSTALLED_APPS:
        from oioioi.portals.models import Portal
        if Portal.objects.filter(owner=shown_user).exists():
            has_portal = True

    sections = []
    for func in profile_registry.items:
        response = func(request, shown_user)

        if isinstance(response, HttpResponseRedirect):
            return response

        if isinstance(response, TemplateResponse):
            sections.append(response.render().content)
        else:
            sections.append(response)

    return TemplateResponse(request, 'gamification/profile.html', {
        'shown_user': shown_user,
        'is_my_friend': is_friend,
        'exp': exp,
        'exp_percentage': int(100 * exp.current_experience /
                              exp.required_experience_to_lvlup),
        'has_portal': has_portal,
        'pending_incoming_friendship_request':
                pending_incoming_friendship_request,
        'sent_friendship_request': sent_friendship_request,
        'sections': sections
    })


@problem_site_tab(_("Shared solutions"), key='shared_solutions', order=400)
def problem_site_shared_solutions(request, problem):
    controller = CodeSharingController()
    submissions = controller.shared_with_me(problem, request.user)
    return TemplateResponse(request,
        'gamification/shared_submissions_tab.html',
        {'submissions': submissions,
         'submissions_on_page': getattr(settings, 'SUBMISSIONS_ON_PAGE', 20)}
    )


def friend_action(request, other_name, action):
    other_user = get_object_or_404(User.objects, username=other_name)
    friends = UserFriends(request.user)

    func = getattr(friends, action)
    if action in ['send_friendship_request', 'remove_friend']:
        func(other_user)
    else:
        friendship_request = friends.request_from(other_user)
        func(friendship_request)

    return redirect('view_profile', username=other_name)


@login_required
@require_POST
def send_friendship_request_view(request, username):
    return friend_action(request, username, 'send_friendship_request')


@login_required
@require_POST
def remove_friend_view(request, username):
    return friend_action(request, username, 'remove_friend')


@login_required
@require_POST
def accept_friendship_request_view(request, username):
    return friend_action(request, username, 'accept_friendship_request')


@login_required
@require_POST
def refuse_friendship_request_view(request, username):
    return friend_action(request, username, 'refuse_friendship_request')


@login_required
def user_problem_exp_view(request, problem_id):
    curr_exp = Experience(request.user)
    try:
        difficulty = ProblemDifficulty.objects.get(problem=problem_id)
        problem_exp = difficulty.experience
    except ProblemDifficulty.DoesNotExist:
        problem_exp = 0
    new_exp = Experience(
        level=curr_exp.current_level,
        experience=curr_exp.current_experience + problem_exp
    )

    if new_exp.current_level == curr_exp.current_level:
        exp_diff_percent = \
            ((new_exp.current_experience - curr_exp.current_experience) /
            curr_exp.required_experience_to_lvlup) * 100
    else:
        whole_levels = \
            (new_exp.current_level - curr_exp.current_level - 1) * 100
        from_curr = \
            100 - ((curr_exp.current_experience /
                    curr_exp.required_experience_to_lvlup) * 100)
        to_expected = (new_exp.current_experience /
                       new_exp.required_experience_to_lvlup) * 100
        exp_diff_percent = whole_levels + from_curr + to_expected

    return JsonResponse({
        'current_exp':
            (curr_exp.current_experience /
            curr_exp.required_experience_to_lvlup) * 100,
        'current_lvl': curr_exp.current_level,
        'exp_to_add': exp_diff_percent
    })
