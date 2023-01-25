from django.utils import timezone
from oioioi.supervision.models import Supervision


def supervision_middleware(get_response):
    """ This should be fairly optimal, as there should be little
        overlapping supervisions (I really don't know how `request` is passed).
        Otherwise, the request.*_rounds should be filtered by the current contest,
        but CurrentContest middleware, which is needed for us to have
        request.contest needs request.supervised_contests.
        Thus, this could be split into 2 middlewares.
    """
    def middleware(request):
        # remember to later check for being a superuser
        relevant=Supervision.objects.filter(
            start_date__lte=timezone.now(),
            end_date__gt=timezone.now(),
        )
        list=relevant.filter(
            group__membership__user_id=request.user.id,
            group__membership__is_present=True,
        ).values_list('round__contest_id', 'round_id')

        request.is_under_supervision=len(list)>0
        if request.is_under_supervision:
            request.supervision_visible_rounds=set()
            request.supervised_contests=set()
            for c,r in list:
                request.supervision_visible_rounds.add(r)
                request.supervised_contests.add(c)
        else:
            request.supervision_hidden_rounds=set(
                relevant.filter(
                    #round__contest_id=request.contest.id,
                ).values_list('round_id', flat=True))
        return get_response(request)

    return middleware
