from oioioi.portals.actions import portal_admin_menu_registry


def portal_processor(request):
    if not hasattr(request, 'portal'):
        return {}

    context = {
        'portal': request.portal,
        'portal_admin_menu': portal_admin_menu_registry,
    }

    if hasattr(request, 'current_node'):
        context['current_node'] = request.current_node

    if request.portal.owner:
        context['navbar_location'] = '~' + request.portal.owner.username

    return context


def portals_main_page_link_visible(request):
    return {'portals_main_page_link_visible': True}
