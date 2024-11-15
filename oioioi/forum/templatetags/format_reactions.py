from django import template
from django.utils.translation import gettext as _
from oioioi.base.utils import get_user_display_name
from django.conf import settings

register = template.Library()

@register.simple_tag
def format_reactions(post, rtype):
  max_count = getattr(settings, 'FORUM_REACTIONS_TO_DISPLAY', 10)

  output = ', '.join([
    get_user_display_name(reaction.author)
    for reaction in 
    post.reactions.filter(type_of_reaction=rtype).select_related('author')[:max_count]
  ])

  count = post.upvotes_count if rtype == 'UPVOTE' else post.downvotes_count
  
  if(count > max_count):
    output += ' ' +  _('and others.')

  return output