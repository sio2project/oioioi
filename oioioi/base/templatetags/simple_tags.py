from django import template
from django.core.urlresolvers import NoReverseMatch, reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def active_url(context, pattern_or_urlname, returned_class='active'):
    """
    Returns returned_class if given pattern or url matches
    context active url.
    .. usage::
     ```
     {% load active_url %}

     <a class="{% active_url 'my_home_page' %}">Home Page</a>
     <a class="{% active_url '^$' %}>Home Page</a>
     ```
    :param context:
    :param pattern_or_urlname: Regex or `name` defined in urls.py
    :param returned_class: A string to return if the url is active
    :return: returned_class or `None`
    """
    try:
        pattern = reverse(pattern_or_urlname)
    except NoReverseMatch:
        pattern = pattern_or_urlname
    path = context['request'].path
    if pattern == path:
        return returned_class
    return ''


@register.simple_tag(takes_context=True)
def site_displayed_tag(context):
    request = context['request']
    if 'first_view_after_logging' in request.session:
        del request.session['first_view_after_logging']
    return ''

# https://stackoverflow.com/questions/28513528/passing-arguments-to-model-methods-in-django-templates
@register.simple_tag
def call_method_with_arguments(obj, method_name, *args):
    return getattr(obj, method_name)(*args)
