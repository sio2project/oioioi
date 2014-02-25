"""Template tags for JSON serialization.

   Example:

    {% load jsonify %}
    {{ msg|jsonify }}

"""

import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='jsonify')
def jsonify(value):
    return mark_safe(json.dumps(value))
