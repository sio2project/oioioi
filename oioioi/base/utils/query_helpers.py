from django.db.models import Q


def Q_always_false():
    return Q(pk__in=[])


def Q_always_true():
    return ~Q_always_false()
