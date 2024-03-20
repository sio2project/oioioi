import itertools

from django.conf import settings
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition
from oioioi.contests.controllers import submission_template_context
from oioioi.contests.models import Submission
from oioioi.contests.utils import (
    can_enter_contest,
    contest_exists,
    has_any_submittable_problem,
    has_any_visible_problem_instance,
    is_contest_archived,
    is_contest_basicadmin,
)
from oioioi.dashboard.contest_dashboard import register_contest_dashboard_view
from oioioi.dashboard.forms import DashboardMessageForm
from oioioi.dashboard.menu import top_links_registry
from oioioi.dashboard.registry import dashboard_headers_registry, dashboard_registry
from oioioi.dashboard.util import get_dashboard_message
from oioioi.questions.views import messages_template_context, visible_messages
from oioioi.rankings.views import has_any_ranking_visible

top_links_registry.register(
    'problems_list',
    _("Problems"),
    lambda request: reverse('problems_list', kwargs={'contest_id': request.contest.id}),
    condition=has_any_visible_problem_instance,
    order=100,
)

top_links_registry.register(
    'submit',
    _("Submit"),
    lambda request: reverse('submit', kwargs={'contest_id': request.contest.id}),
    condition=has_any_submittable_problem & ~is_contest_archived,
    order=200,
)

top_links_registry.register(
    'ranking',
    _("Ranking"),
    lambda request: reverse(
        'default_ranking', kwargs={'contest_id': request.contest.id}
    ),
    condition=has_any_ranking_visible,
    order=300,
)


@enforce_condition(contest_exists & is_contest_basicadmin)
def dashboard_message_edit_view(request):
    instance = get_dashboard_message(request)
    if request.method == 'POST':
        form = DashboardMessageForm(request, request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect('contest_dashboard', contest_id=request.contest.id)
    else:
        form = DashboardMessageForm(request, instance=instance)
    return TemplateResponse(
        request,
        'public_message/edit.html',
        {'form': form, 'title': _('Edit dashboard message')}
    )


@dashboard_registry.register_decorator(order=10)
def dashboard_message_fragment(request):
    if request.contest is None:
        return None
    instance = get_dashboard_message(request)
    is_admin = is_contest_basicadmin(request)
    content = ''
    if instance and instance.content:
        content = instance.content

    if not content and not is_admin:
        return ''

    context = {
        'content': content,
        'is_admin': is_admin,
    }
    return render_to_string(
        'dashboard/dashboard-message.html', context=context, request=request
    )


@dashboard_headers_registry.register_decorator(order=100)
def top_links_fragment(request):
    top_links = top_links_registry.template_context(request)
    context = {
        'top_links': top_links,
    }
    return render_to_string(
        'dashboard/dashboard-actions.html', context=context, request=request
    )


@dashboard_registry.register_decorator(order=100)
def submissions_fragment(request):
    if not request.user.is_authenticated:
        return None
    submissions = (
        Submission.objects.filter(problem_instance__contest=request.contest)
        .order_by('-date')
        .select_related()
    )
    cc = request.contest.controller
    submissions = cc.filter_my_visible_submissions(request, submissions)
    submissions = submissions[: getattr(settings, 'NUM_DASHBOARD_SUBMISSIONS', 8)]
    if not submissions:
        return None
    submissions = [submission_template_context(request, s) for s in submissions]
    show_scores = any(s['can_see_score'] for s in submissions)
    context = {'submissions': submissions, 'show_scores': show_scores}
    return render_to_string(
        'dashboard/dashboard-submissions.html', context=context, request=request
    )


@dashboard_registry.register_decorator(order=200)
def messages_fragment(request):
    messages = messages_template_context(request, visible_messages(request))
    dashboard_msg_cnt_limit = getattr(settings, 'NUM_DASHBOARD_MESSAGES', 8)
    show_more_button = len(messages) > dashboard_msg_cnt_limit
    messages = messages[:dashboard_msg_cnt_limit]
    if not messages:
        return None
    context = {
        'records': messages,
        'show_more_button': show_more_button,
    }
    return render_to_string('dashboard/messages.html', context=context, request=request)


@menu_registry.register_decorator(
    _("Dashboard"),
    lambda request: reverse(
        'contest_dashboard', kwargs={'contest_id': request.contest.id}
    ),
    order=20,
    condition=contest_exists & can_enter_contest,
)
@register_contest_dashboard_view(100)
@enforce_condition(contest_exists & can_enter_contest)
def public_contest_dashboard_view(request):
    headers = [gen(request) for gen in dashboard_headers_registry]
    headers = [hdr for hdr in headers if hdr is not None]
    fragments = [gen(request) for gen in dashboard_registry]
    fragments = [frag for frag in fragments if frag is not None]
    if not fragments:
        fragments = [
            render_to_string('dashboard/dashboard-empty.html', request=request)
        ]
    context = {
        'headers': headers,
        'fragments': fragments,
    }
    return TemplateResponse(request, 'dashboard/dashboard.html', context)
