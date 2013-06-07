from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def site_displayed_tag(context):
    request = context['request']
    if 'first_view_after_logging' in request.session:
        del request.session['first_view_after_logging']
    return ''
