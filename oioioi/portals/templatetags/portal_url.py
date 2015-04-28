from django.template import Library
from oioioi.portals.actions import portal_url


register = Library()
register.simple_tag(portal_url)
