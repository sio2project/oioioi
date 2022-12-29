from django.core.cache import cache
from django.utils import timezone

from oioioi.supervision.models import Supervision


def related_supervisions(user):
    return Supervision.objects.filter(
        start_date__lte=timezone.now(),
        end_date__gt=timezone.now(),
        group__membership__user_id=user.id,
        group__membership__is_present=True,
    )


def is_user_under_supervision(user):
    if user.is_anonymous or user.is_superuser:
        return False
    key = "oioioi.supervision.utils.user." + str(user.id)
    ret = cache.get(key)
    if ret == None:
        ret = related_supervisions(user).exists()
        cache.set(key, ret, 3)
    return ret


def is_round_under_supervision(round_):
    return Supervision.objects.filter(
        start_date__lte=timezone.now(), end_date__gt=timezone.now(), round=round_
    ).exists()


def can_user_enter_round(user, round_):
    key = "oioioi.supervision.utils.round." + str(user.id) + "." + str(round_.id)
    ret = cache.get(key)
    if ret == None:
        if not (is_user_under_supervision(user) or is_round_under_supervision(round_)):
            ret = True
        else:
            ret = related_supervisions(user).filter(round=round_).exists()
        cache.set(key, ret, 3)
    return ret


def can_user_enter_contest(user, contest):
    """Block other contests for users under supervision."""
    if not is_user_under_supervision(user):
        return True

    return related_supervisions(user).filter(round__contest=contest).exists()


def get_user_supervised_contests(user):
    return related_supervisions(user).values_list('round__contest', flat=True)
