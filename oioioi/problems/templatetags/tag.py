from django.template import Library
from django.utils.html import format_html

from oioioi.base.utils.tags import get_tag_prefix

register = Library()


@register.simple_tag
def tag_label(tag):
    prefix = get_tag_prefix(tag)
    return format_html(
        u'<a title="{tooltip}" class="label tag-label-{cls}" href="{href}" '
        '>{name}</a>',
        tooltip=getattr(tag, 'full_name', tag.name),
        name=tag.name,
        cls=prefix,
        href="?q=tag:" + tag.name
    )


@register.simple_tag
def origininfo_label(info):
    prefix = get_tag_prefix(info)
    return format_html(
        u'<a title="{tooltip}" class="label tag-label-{cls}" href="{href}" '
        '>{name}</a>',
        tooltip=info.full_name,
        name=info.value,
        cls=prefix,
        href="?" + prefix + "=" + info.name
    )
