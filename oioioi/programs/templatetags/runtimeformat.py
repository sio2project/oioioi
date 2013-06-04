from django import template

register = template.Library()


@register.filter
def runtimeformat(value):
    if value is None:
        return '???'
    return '%.2fs' % (value / 1000.0,)
