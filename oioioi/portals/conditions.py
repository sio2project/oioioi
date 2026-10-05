from django.conf import settings

from oioioi.base.permissions import make_request_condition
from oioioi.portals.models import Portal


@make_request_condition
def is_portal_admin(request):
    user = request.user
    return user.is_superuser or user == request.portal.owner


@make_request_condition
def current_node_is_root(request):
    return request.current_node.is_root_node()


@make_request_condition
def main_page_from_default_global_portal(request):
    return settings.DEFAULT_GLOBAL_PORTAL_AS_MAIN_PAGE and Portal.objects.filter(owner=None, link_name="default").exists()
