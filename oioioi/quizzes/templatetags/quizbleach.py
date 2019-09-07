from django.template import Library
from django.utils.safestring import mark_safe

import bleach

register = Library()

ALLOWED_TAGS = bleach.ALLOWED_TAGS + ['br', 'pre', 'tt', 'hr']
ALLOWED_ATTRIBUTES = bleach.ALLOWED_ATTRIBUTES

@register.filter
def quizbleach(text):
    return mark_safe(bleach.clean(text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES))

