"""Template tags for working with strings.

   Example:

    {% load stringutils %}
    {{ msg|indent }}

"""

from django import template

register = template.Library()


@register.filter(name='indent')
def indent_string(value, num_spaces=4):
    """Adds ``num_spaces`` spaces at the
       beginning of every line in value."""
    return ' '*num_spaces + value.replace('\n', '\n' + ' '*num_spaces)
