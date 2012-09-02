from django.conf import settings
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Submission
from oioioi.contests.utils import enter_contest_permission_required
from oioioi.contests.controllers import ContestController
from oioioi.contests.views import submission_template_context
from oioioi.rankings.views import any_ranking_visible
from oioioi.base.menu import MenuRegistry, menu_registry
from oioioi.messages.views import messages_template_context, \
        visible_messages
import itertools

top_links_registry = MenuRegistry()

top_links_registry.register('problems_list', _("Problems"),
        lambda request: reverse('problems_list', kwargs={'contest_id':
            request.contest.id}), order=100)

top_links_registry.register('submit', _("Submit"),
        lambda request: reverse('submit', kwargs={'contest_id':
            request.contest.id}), order=200)

top_links_registry.register('ranking', _("Ranking"),
        lambda request: reverse('default_ranking', kwargs={'contest_id':
            request.contest.id}), condition=any_ranking_visible,
        order=200)

menu_registry.register('dashboard', _("Dashboard"),
        lambda request: reverse('contest_dashboard', kwargs={'contest_id':
            request.contest.id}), order=20)

# http://stackoverflow.com/questions/1624883/alternative-way-to-split-a-list-into-groups-of-n
def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return list(itertools.izip_longest(*args, fillvalue=fillvalue))

@enter_contest_permission_required
def contest_dashboard_view(request, contest_id):
    top_links = grouper(3, top_links_registry.template_context(request))
    submissions = Submission.objects \
            .filter(problem_instance__contest=request.contest) \
            .order_by('-date').select_related()
    controller = request.contest.controller
    submissions = controller.filter_visible_submissions(request, submissions)
    submissions = submissions[:getattr(settings, 'NUM_DASHBOARD_SUBMISSIONS', 8)]
    submissions = [submission_template_context(request, s) for s in submissions]
    show_scores = bool(s for s in submissions if s.score is not None)
    messages = messages_template_context(request, visible_messages(request))
    context = {
            'top_links': top_links,
            'submissions': submissions,
            'records': messages,
            'show_scores': show_scores
        }
    return render_to_response('dashboard/dashboard.html',
            context_instance=RequestContext(request, context))
