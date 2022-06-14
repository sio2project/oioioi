from django.db.models import prefetch_related_objects
from django.template import Library
from django.utils.html import format_html
from oioioi.base.utils.tags import get_tag_name, get_tag_prefix

register = Library()


@register.simple_tag
def prefetch_tags(problems):
    prefetch_related_objects(
        problems,
        'difficultytag_set',
        'algorithmtag_set__localizations',
        'origintag_set__localizations',
        'origininfovalue_set__localizations',
        'origininfovalue_set__parent_tag__localizations',
    )
    return u''


@register.simple_tag
def tag_label(tag):
    prefix = get_tag_prefix(tag)
    return format_html(
        u'<a title="{tooltip}" class="badge tag-label tag-label-{cls}" href="{href}" '
        '>{name}</a>',
        tooltip=getattr(tag, 'full_name', tag.name),
        name=get_tag_name(tag),
        cls=prefix,
        href="?" + prefix + "=" + tag.name,
    )


@register.simple_tag
def origininfo_label(info):
    prefix = get_tag_prefix(info)
    return format_html(
        u'<a title="{tooltip}" class="badge tag-label tag-label-{cls}" href="{href}" '
        '>{name}</a>',
        tooltip=info.full_name,
        name=info.value,
        cls=prefix,
        href="?" + prefix + "=" + info.name,
    )
