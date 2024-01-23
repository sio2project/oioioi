from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition, make_request_condition
from oioioi.base.utils.user_selection import get_user_hints_view
from oioioi.contests.models import Submission
from oioioi.contests.utils import (
    can_enter_contest,
    contest_exists,
    is_contest_basicadmin,
)
from oioioi.rankings.forms import FilterUsersInRankingForm, RankingMessageForm
from oioioi.rankings.models import Ranking
from oioioi.rankings.utils import get_ranking_message


@make_request_condition
def has_any_ranking_visible(request):
    ccontroller = request.contest.controller
    rcontroller = ccontroller.ranking_controller()
    return ccontroller.can_see_ranking(request) and bool(
        rcontroller.available_rankings(request)
    )


@enforce_condition(contest_exists & can_enter_contest & is_contest_basicadmin)
@enforce_condition(has_any_ranking_visible)
def get_users_in_ranking_view(request):
    queryset = Submission.objects
    return get_user_hints_view(request, 'substr', queryset, 'user')


@menu_registry.register_decorator(
    _("Ranking"),
    lambda request: reverse(
        'default_ranking', kwargs={'contest_id': request.contest.id}
    ),
    order=440,
)
@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(has_any_ranking_visible, template='rankings/no_rankings.html')
def ranking_view(request, key=None):
    rcontroller = request.contest.controller.ranking_controller()
    choices = rcontroller.available_rankings(request)
    if key is None:
        key = choices[0][0]
    if key not in next(zip(*choices)):
        raise Http404

    context = dict()

    ranking = None

    if rcontroller.can_search_for_users():
        form = FilterUsersInRankingForm(request, request.GET)
        context['form'] = form

        if form.is_valid():
            user = form.cleaned_data.get('user')
            # Everybody can search for themselves.
            # Contest admins can search for anyone.
            if user and (is_contest_basicadmin(request) or user == request.user):
                found_pos = rcontroller.find_user_position(request, key, user)
                if found_pos:
                    users_per_page = getattr(settings, 'PARTICIPANTS_ON_PAGE', 100)
                    found_page = ((found_pos - 1) // users_per_page) + 1
                    get_dict = request.GET.copy()
                    get_dict.pop('user')
                    get_dict['page'] = str(found_page)
                    return redirect(
                        request.path + '?' + get_dict.urlencode() + '#' + str(user.id)
                    )
                else:
                    msg = _("User is not in the ranking.")
                    # Admin should receive error in form,
                    # whereas user should see it as an error message,
                    # because there is no form then.
                    if is_contest_basicadmin(request):
                        form._errors['user'] = form.error_class([msg])
                    else:
                        messages.error(request, msg)

    if ranking is None:
        # Changing request.GET is necessary!
        # The pagination library not only truncates the list of objects,
        # but also generates the links to other pages.
        # It simply copies the current url and replaces 'page'
        # with another number. If there is a different GET parameter,
        # it is included (without any change) in the url to another page.

        # If a user requests a page, he can provide any number of useless
        # GET parameters, which will be shown in urls to other pages.
        # The ranking page could be cached and those urls could be
        # visible to other users, giving them links to the ranking
        # with strange arguments (e.g. arguments, which perform a search).

        # Below, only 'user' key is deleted, because that's the only argument
        # performing an action, and I'd like to change request.GET
        # as less as possible.
        # This solution does not prevent users from sending "messages"
        # between each other (using these GET parameters).
        request.GET = request.GET.copy()
        try:
            request.GET.pop('user')
        except KeyError:
            pass
        ranking = rcontroller.get_rendered_ranking(request, key)

    context['choices'] = choices
    context['ranking'] = ranking
    context['key'] = key
    context['message'] = get_ranking_message(request)

    return TemplateResponse(request, 'rankings/ranking_view.html', context)


@enforce_condition(contest_exists & is_contest_basicadmin)
def ranking_csv_view(request, key):
    rcontroller = request.contest.controller.ranking_controller()
    choices = rcontroller.available_rankings(request)
    if not choices or key not in next(zip(*choices)):
        raise Http404

    return rcontroller.render_ranking_to_csv(request, key)


@enforce_condition(contest_exists & is_contest_basicadmin)
@require_POST
def ranking_invalidate_view(request, key):
    rcontroller = request.contest.controller.ranking_controller()
    full_key = rcontroller.get_full_key(request, key)
    ranking = Ranking.objects.filter(key=full_key)
    Ranking.invalidate_queryset(ranking)
    return redirect('ranking', key=key)


@enforce_condition(contest_exists & is_contest_basicadmin)
def edit_ranking_message_view(request):
    instance = get_ranking_message(request)
    if request.method == 'POST':
        form = RankingMessageForm(request, request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect('default_ranking', contest_id=request.contest.id)
    else:
        form = RankingMessageForm(request, instance=instance)
    return TemplateResponse(
        request,
        'public_message/edit.html',
        {'form': form, 'title': _("Edit ranking message")},
    )
