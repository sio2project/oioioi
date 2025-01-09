from django import template
from django.utils.translation import gettext as _
from oioioi.base.utils import get_user_display_name
from oioioi.forum.models import POST_REACTION_TO_PREFETCH_ATTR, POST_REACTION_TO_COUNT_ATTR
from django.conf import settings

register = template.Library()

@register.simple_tag
def display_reacted_by(post, rtype):
  if(rtype not in POST_REACTION_TO_PREFETCH_ATTR):
    raise ValueError('Invalid reaction type in template:' + rtype)

  output = ', '.join([
    get_user_display_name(reaction.author)
    for reaction in getattr(post, POST_REACTION_TO_PREFETCH_ATTR[rtype])
  ])

  count = getattr(post, POST_REACTION_TO_COUNT_ATTR[rtype])
  max_count = getattr(settings, 'FORUM_REACTIONS_TO_DISPLAY', 10)
  
  if(count > max_count):
    output += ' ' +  _('and others.')

  return output