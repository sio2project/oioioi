from django import template
from django.conf import settings


register = template.Library()


@register.inclusion_tag('contests/navbar-user-info-form.html',
                        takes_context=True)
def user_info_dropdown_form(context):
    return {
        'ctx': context,
        'num_hints': getattr(settings, 'NUM_HINTS', 10),
    }
