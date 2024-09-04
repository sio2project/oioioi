from django import template
from django.conf import settings

register = template.Library()


@register.inclusion_tag('su/navbar-su-form.html', takes_context=True)
def su_dropdown_form(context):
    from oioioi.su.forms import SuForm
    from oioioi.su.utils import is_under_su, can_contest_admins_su
    from oioioi.contests.utils import is_contest_basicadmin, contest_exists

    request = context['request']
    is_valid_contest_admin = (
        can_contest_admins_su(request) and
        contest_exists(request) and
        is_contest_basicadmin(request)
    )

    return {
        'ctx': context,
        'form': SuForm(auto_id='su-%s'),
        'is_under_su': is_under_su(context['request']),
        'num_hints': getattr(settings, 'NUM_HINTS', 10),
        'is_valid_contest_admin': is_valid_contest_admin,
    }
