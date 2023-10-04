from django.conf import settings
from django.urls import reverse
from django.utils.functional import lazy
from django.utils.translation import ngettext
from oioioi.base.utils import make_navbar_badge
from oioioi.contests.models import ProblemInstance
from oioioi.contests.utils import is_contest_basicadmin
from oioioi.problems.utils import can_add_to_problemset


def dangling_problems_processor(request):
    if not getattr(request, 'contest', None):
        return {}
    if not is_contest_basicadmin(request):
        return {}

    dangling_pis = ProblemInstance.objects.filter(contest=request.contest,
            round__isnull=True)
    count = dangling_pis.count()
    def generator():
        if not count:
            return ''
        elif count == 1:
            pi = dangling_pis.get()
            link = reverse(
                'oioioiadmin:contests_probleminstance_change',
                args=(pi.id,),
            )
            if request.path == link:
                return ''
        else:
            link = reverse('oioioiadmin:contests_probleminstance_changelist')
        text = ngettext(
            '%(count)d PROBLEM WITHOUT ROUND',
            '%(count)d PROBLEMS WITHOUT ROUNDS',
            count,
        )
        text = text % {'count': count}
        return make_navbar_badge(link, text)

    return {'extra_navbar_right_dangling_problems': lazy(generator, str)()}


def problemset_link_visible_processor(request):
    return {'is_problemset_link_visible': settings.PROBLEMSET_LINK_VISIBLE}


def problems_need_rejudge_processor(request):
    if not getattr(request, 'contest', None):
        return {}
    if not is_contest_basicadmin(request):
        return {}

    pis = ProblemInstance.objects.filter(contest=request.contest,
            needs_rejudge=True)
    count = pis.count()
    def generator():
        if not count:
            return ''
        else:
            link = reverse('oioioiadmin:contests_probleminstance_changelist')
        text = ngettext(
            "%(count)d PROBLEM NEEDS REJUDGING",
            "%(count)d PROBLEMS NEED REJUDGING",
            count,
        )
        text = text % {'count': count}
        return make_navbar_badge(link, text)

    return {
        'extra_navbar_right_not_rejudged_problems': lazy(generator, str)()
    }


def can_add_to_problemset_processor(request):
    return {'can_add_to_problemset': can_add_to_problemset(request)}
