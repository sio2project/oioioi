import bleach
from django.utils.safestring import mark_safe

ALLOWED_TAGS = frozenset(list(bleach.ALLOWED_TAGS) + ['br', 'pre', 'tt', 'hr'])
ALLOWED_ATTRIBUTES = bleach.ALLOWED_ATTRIBUTES


def quizbleach(text):
    return mark_safe(
        bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    )
