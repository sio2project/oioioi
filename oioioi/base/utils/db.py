from functools import wraps

from django.db import transaction


def require_transaction(function):
    @wraps(function)
    def decorated(*args, **kwargs):
        assert transaction.get_connection().in_atomic_block
        return function(*args, **kwargs)
    return decorated
