from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.contests.utils import (
    can_enter_contest,
    contest_exists,
    get_submission_or_error,
)
from oioioi.publicsolutions.forms import FilterPublicSolutionsForm
from oioioi.publicsolutions.models import VoluntarySolutionPublication
from oioioi.publicsolutions.utils import (
    any_round_public,
    get_may_be_published_solutions_for_user,
    get_public_solutions,
    solution_may_be_published,
)


@menu_registry.register_decorator(
    _("Solutions"),
    lambda request: reverse(
        'list_solutions', kwargs={'contest_id': request.contest.id}
    ),
    order=1000,
)
@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(any_round_public)
def list_solutions_view(request):
    form = FilterPublicSolutionsForm(request, request.GET)

    category = None
    if form.is_valid():
        category = form.cleaned_data['category']

    subs = get_public_solutions(request)
    if category:
        subs = subs.filter(problem_instance=category)
    subs = subs.order_by('user__last_name', 'user__first_name', 'problem_instance')

    context = {
        'form': form,
        'submissions': subs,
        'submissions_on_page': getattr(settings, 'SUBMISSIONS_ON_PAGE', 100),
        'may_publish_any': get_may_be_published_solutions_for_user(request).exists(),
    }

    return TemplateResponse(request, 'publicsolutions/list-solutions.html', context)


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(any_round_public)
def publish_solutions_view(request):
    subs = get_may_be_published_solutions_for_user(request).order_by(
        'problem_instance', 'date'
    )

    return TemplateResponse(
        request,
        'publicsolutions/publish.html',
        {
            'submissions': subs,
            'submissions_on_page': getattr(settings, 'SUBMISSIONS_ON_PAGE', 100),
        },
    )


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(any_round_public & solution_may_be_published)
@require_POST
def publish_solution_view(request, submission_id):
    submission = get_submission_or_error(request, submission_id)

    _pub, _created = VoluntarySolutionPublication.objects.get_or_create(
        submission=submission
    )

    return redirect('publish_solutions', contest_id=request.contest.id)


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(any_round_public & solution_may_be_published)
@require_POST
def unpublish_solution_view(request, submission_id):
    submission = get_submission_or_error(request, submission_id)

    pub, _created = VoluntarySolutionPublication.objects.get_or_create(
        submission=submission
    )

    pub.delete()
    return redirect('publish_solutions', contest_id=request.contest.id)
