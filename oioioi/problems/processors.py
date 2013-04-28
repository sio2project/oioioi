from django.template import Template, Context
from django.core.urlresolvers import reverse
from django.utils.translation import ungettext
from django.utils.functional import lazy
from oioioi.base.utils import make_navbar_badge
from oioioi.contests.models import ProblemInstance

def dangling_problems_processor(request):
    if not getattr(request, 'contest', None):
        return {}
    if not request.user.has_perm('contests.contest_admin', request.contest):
        return {}
    def generator():
        dangling_pis = ProblemInstance.objects.filter(contest=request.contest,
                round__isnull=True)
        count = dangling_pis.count()
        if not count:
            return ''
        elif count == 1:
            pi = dangling_pis.get()
            link = reverse('oioioiadmin:contests_probleminstance_change',
                        args=(pi.id,))
            if request.path == link:
                return ''
        else:
            link = reverse('oioioiadmin:contests_probleminstance_changelist')
        text = ungettext('%(count)d PROBLEM WITHOUT ROUND',
                '%(count)d PROBLEMS WITHOUT ROUNDS',
                count) % {'count': count}
        return make_navbar_badge(link, text)
    return {'extra_navbar_right_dangling_problems': lazy(generator, unicode)()}

