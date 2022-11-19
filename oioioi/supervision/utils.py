from django.utils import timezone

from oioioi.supervision.models import Supervision


def is_user_under_supervision(user):
    if user.is_anonymous() or user.is_superuser:
        return False

    return Supervision.objects.filter(
        start_date__lte=timezone.now(),
        end_date__gt=timezone.now(),
        group__membership__user=user
    ).exists()


def is_round_under_supervision(round_):
    return Supervision.objects.filter(
        start_date__lte=timezone.now(),
        end_date__gt=timezone.now(),
        round=round_
    ).exists()


def can_user_enter_round(user, round_):
    if user.is_anonymous():
        return False

    if not (is_user_under_supervision(user) or
            is_round_under_supervision(round_)):
        return True

    return Supervision.objects.filter(
        start_date__lte=timezone.now(),
        end_date__gt=timezone.now(),
        round=round_,
        group__membership__user=user,
        group__membership__is_present=True
    ).exists()


def can_user_enter_contest(user, contest):
    """Block other contests for users under supervision."""
    if not is_user_under_supervision(user):
        return True

    return Supervision.objects.filter(
        start_date__lte=timezone.now(),
        end_date__gt=timezone.now(),
        round__contest=contest,
        group__membership__user=user,
        group__membership__is_present=True
    ).exists()


def get_user_supervised_contests(user):
    return Supervision.objects.filter(
        start_date__lte=timezone.now(),
        end_date__gt=timezone.now(),
        group__membership__user=user,
        group__membership__is_present=True
    ).values_list('round__contest', flat=True)
