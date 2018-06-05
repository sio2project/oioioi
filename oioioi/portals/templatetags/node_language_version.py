from django import template

register = template.Library()


@register.filter
def full_name(node, request):
    return node.get_lang_version(request).full_name


@register.filter
def panel_code(node, request):
    return node.get_lang_version(request).panel_code
