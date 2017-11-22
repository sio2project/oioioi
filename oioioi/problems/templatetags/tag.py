from django.template import Library
from django.utils.html import format_html

from oioioi.base.utils.tags import get_tag_colors

register = Library()


@register.simple_tag
def tag_label(tag):
    colors = get_tag_colors(tag.name)
    return format_html(
        '<span title="{name}" class="label" style="background-color: '
        '{bgcolor}; color: {textcolor};">{name}</span>',
        name=tag.name,
        bgcolor=colors[0],
        textcolor=colors[1]
    )
