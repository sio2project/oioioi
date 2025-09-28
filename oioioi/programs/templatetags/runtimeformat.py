from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.filter
def runtimeformat(value):
    if value is None:
        return "???"
    seconds = value / 1000.0
    if seconds < 200:
        return _("%(seconds).2fs") % {"seconds": seconds}
    else:
        return _("%(minutes)dm %(seconds).2fs") % {"minutes": int(seconds // 60), "seconds": (seconds % 60)}
