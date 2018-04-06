from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from oioioi.base.main_page import register_main_page_view
from oioioi.szkopul.menu import navbar_links_registry

navbar_links_registry.register(
    name='problemset',
    text=_('Problemset'),
    url_generator=lambda request: reverse('problemset_main'),
    order=100,
)

navbar_links_registry.register(
    name='task_archive',
    text=_('Task archive'),
    # TODO Change the following URL when the Task Archive
    #      gets moved from the global portal on Szkopul.
    url_generator=lambda request:
        'https://szkopul.edu.pl/portal/problemset' +
        ('_eng' if request.LANGUAGE_CODE != 'pl' else ''),
    order=200,
)

# TODO Add Portals main page to the menu:
# navbar_links_registry.register(
#     name='portals',
#     text=_('Portals'),
#     ...
# )


@register_main_page_view(order=100)
def main_page_view(request):
    navbar_links = navbar_links_registry.template_context(request)
    context = {
        'navbar_links': navbar_links,
    }
    return TemplateResponse(request, 'main-page.html', context)
