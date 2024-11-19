from django import template
from django.utils.translation import gettext as _
from oioioi.base.utils import get_user_display_name
from django.conf import settings

register = template.Library()

@register.simple_tag
def display_reacted_by(post, rtype):
  # post needs to be queried with prefetch_reacted_by

  output = ', '.join([
    get_user_display_name(reaction.author)
    for reaction in getattr(post, rtype.lower() + 'd_by')
  ])

  count = getattr(post, rtype.lower() + 's_count')
  max_count = getattr(settings, 'FORUM_REACTIONS_TO_DISPLAY', 10)
  
  if(count > max_count):
    output += ' ' +  _('and others.')

  return output