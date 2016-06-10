from django import template
from django.utils.translation import ugettext_lazy as _

register = template.Library()


@register.filter
def runtimeformat(value):
    if value is None:
        return '???'
    seconds = value / 1000.0
    if seconds < 200:
        return _("%(seconds).2fs") % dict(seconds=seconds)
    else:
        return _("%(minutes)dm %(seconds).2fs") % dict(
                minutes=int(seconds / 60), seconds=(seconds % 60))
