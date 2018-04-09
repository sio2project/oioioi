from django.template import Library
from django.utils.html import format_html

from oioioi.base.utils.tags import get_tag_colors

register = Library()


@register.simple_tag
def tag_label(tag):
    colors = get_tag_colors(tag.name)
    return format_html(
        '<a title="{name}" class="label" href="{href}" '
        'style="background-color: {bgcolor}; color: {textcolor};">{name}</a>',
        name=tag.name,
        bgcolor=colors[0],
        textcolor=colors[1],
        href="?q=tag:" + tag.name
    )
