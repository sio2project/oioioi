from django.db.models import Prefetch, prefetch_related_objects
from django.template import Library
from django.utils.html import format_html
from oioioi.base.utils.tags import get_tag_name, get_tag_prefix
from oioioi.problems.models import AggregatedAlgorithmTagProposal
from django.utils.translation import gettext as _, ngettext
from django.conf import settings

register = Library()


@register.simple_tag
def prefetch_top_tag_proposals(problems):
    max_proposals_shown = settings.PROBSET_SHOWN_TAG_PROPOSALS_LIMIT
    min_proposals_per_tag = settings.PROBSET_MIN_AMOUNT_TO_CONSIDER_TAG_PROPOSAL

    prefetch_related_objects(
        problems,
        Prefetch(
            'aggregatedalgorithmtagproposal_set',
            queryset=AggregatedAlgorithmTagProposal.objects.filter(
                amount__gte=min_proposals_per_tag
            ).order_by('-amount')[:max_proposals_shown],
            to_attr='top_tag_proposals'
        )
    )

    for problem in problems:
        algo_tag_pks = set(problem.algorithmtag_set.all().values_list('pk', flat=True))
        problem.top_tag_proposals = [
            proposal for proposal in problem.top_tag_proposals
            if proposal.tag.pk not in algo_tag_pks
        ]

    return u''


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
        '<a title="{tooltip}" class="badge tag-label tag-label-{cls}" href="{href}" '
        '>{name}</a>',
        tooltip=getattr(tag, 'full_name', tag.name),
        name=get_tag_name(tag),
        cls=prefix,
        href="?" + prefix + "=" + tag.name,
    )


@register.simple_tag
def aggregated_tag_label(aggregated_tag):
    amount = aggregated_tag.amount
    tag = aggregated_tag.tag

    full_prefix = get_tag_prefix(aggregated_tag)
    tag_prefix = get_tag_prefix(tag)

    tag_tooltip = getattr(tag, 'full_name', tag.name)
    times_text = ngettext("1 time", "%(count)d times", amount) % {'count': amount}
    return format_html(
        '<a title="{tooltip}" class="badge tag-label tag-label-{cls} position-relative" href="{href}">'
        '{name}<span class="tag-proposal-amount badge">{amount}</span></a>',
        tooltip=_(f"{tag_tooltip} — proposed {times_text}"),
        name=get_tag_name(tag),
        cls=full_prefix,
        amount=str(amount),
        href="?" + tag_prefix + "=" + tag.name + "&include_proposals=1",
    )


@register.simple_tag
def origininfo_label(info):
    prefix = get_tag_prefix(info)
    return format_html(
        '<a title="{tooltip}" class="badge tag-label tag-label-{cls}" href="{href}" '
        '>{name}</a>',
        tooltip=info.full_name,
        name=info.value,
        cls=prefix,
        href="?" + prefix + "=" + info.name,
    )
