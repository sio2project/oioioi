from django import template
from django.utils.translation import ugettext_lazy as _

register = template.Library()


@register.filter
def runtimeformat(value):
    if value is None:
        return '???'
    seconds = value / 1000.0
    if seconds < 200:
        return _("%.2fs") % (seconds,)
    else:
        return _("%dm %.2fs") % (int(seconds / 60), seconds % 60)
