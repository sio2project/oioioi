from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.filter
def memoryformat(value):
    if value is None:
        return "???"
    mebibytes = value / 1024.0
    if mebibytes < 10:
        return _("%(mebibytes).1fMiB") % {"mebibytes": mebibytes}
    else:
        return _("%(mebibytes)dMiB") % {"mebibytes": mebibytes}
