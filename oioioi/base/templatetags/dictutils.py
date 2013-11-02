"""Simple tag for dictionary lookups

   Example:

    {% load dictutils %}
    {{ dict|lookup:key }}

"""

from django import template

register = template.Library()


@register.filter(name='lookup')
def lookup(d, key):
    """Lookup value from dictionary"""
    return d[key]
