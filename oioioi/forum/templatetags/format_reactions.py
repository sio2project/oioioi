from django import template
from django.utils.translation import gettext as _
from oioioi.base.utils import get_user_display_name

register = template.Library()

@register.simple_tag
def format_reactions(post, rtype):
  output = ', '.join([
    get_user_display_name(reaction.author)
    for reaction in 
    post.reactions.filter(type_of_reaction=rtype).select_related('author')[:10]
  ])

  if(post.reactions.filter(type_of_reaction=rtype).count() > 10):
    output +=  _(' and others')

  return output