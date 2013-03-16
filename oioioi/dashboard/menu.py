from django.utils.translation import ugettext_lazy as _
from oioioi.base.menu import MenuRegistry
from oioioi.base.permissions import not_anonymous

top_links_registry = MenuRegistry(_("Top Links Menu"),
    lambda request: hasattr(request, 'contest') and not_anonymous(request))
