from django import template
from django.utils import timezone

register = template.Library()


@register.inclusion_tag("clock/navbar-clock.html", takes_context=True)
def navbar_clock(context):
    timestamp = getattr(context["request"], "timestamp", None)
    if not timestamp:
        return {}
    if "admin_time" in context["request"].session:
        return {
            "current_time": timezone.localtime(timestamp).strftime("%x %X"),
            "is_admin_time_set": True,
        }
    return {
        "current_time": timezone.localtime(timestamp).strftime("%X"),
        "is_admin_time_set": False,
    }


@register.inclusion_tag("clock/navbar-admin-clock.html", takes_context=True)
def navbar_admin_clock(context):
    result = navbar_clock(context)
    result["path"] = context["request"].get_full_path()
    return result


@register.inclusion_tag("clock/navbar-countdown.html", takes_context=True)
def navbar_countdown(context):
    return {}
