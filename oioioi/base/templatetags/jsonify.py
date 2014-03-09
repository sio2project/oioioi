"""Template tags for JSON serialization.

   Example:

    {% load jsonify %}
    {{ msg|jsonify }}

"""

import json

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escapejs

register = template.Library()


@register.filter(name='jsonify')
def jsonify(value):
    """Be careful when using it directly in js! Code like that:

        <script>
            var x = {{ some_user_data|jsonify }};
        </script>

       contains an XSS vunerability. That's because browsers
       will interpret </script> tag inside js string.
    """
    return mark_safe(json.dumps(value))


@register.filter(name='json_parse')
def json_parse(value):
    """This is a correct way of embedding json inside js in an HTML template.
    """
    return mark_safe('JSON.parse(\'%s\')' % escapejs(json.dumps(value)))
