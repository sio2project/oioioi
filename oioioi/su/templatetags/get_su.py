from django import template
from django.conf import settings

register = template.Library()


@register.inclusion_tag("su/navbar-su-form.html", takes_context=True)
def su_dropdown_form(context):
    from oioioi.contests.utils import contest_exists, is_contest_basicadmin
    from oioioi.su.forms import SuForm
    from oioioi.su.utils import can_contest_admins_su, is_real_superuser, is_under_su

    request = context["request"]
    # Checking if real user is a superuser blocks the ability to switch when switched to contest admin.
    is_valid_contest_admin = can_contest_admins_su(request) and contest_exists(request) and is_contest_basicadmin(request) and not is_real_superuser(request)

    return {
        "ctx": context,
        "form": SuForm(auto_id="su-%s"),
        "is_under_su": is_under_su(context["request"]),
        "num_hints": getattr(settings, "NUM_HINTS", 10),
        "is_valid_contest_admin": is_valid_contest_admin,
    }
