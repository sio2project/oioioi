import bleach
from django.utils.safestring import mark_safe

ALLOWED_TAGS = bleach.ALLOWED_TAGS.union(['br', 'pre', 'tt', 'hr'])
ALLOWED_ATTRIBUTES = bleach.ALLOWED_ATTRIBUTES


def quizbleach(text):
    return mark_safe(
        bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    )
