from django.template import Template, Context
from django.utils.functional import lazy
from oioioi.contestlogo.models import ContestLogo

TEMPLATE = '<div id="contestlogo"><img src="{{ url }}"></div>'

def logo_processor(request):
    if not getattr(request, 'contest', None):
        return {}
    def generator():
        try:
            instance = ContestLogo.objects.get(contest=request.contest)
            context = Context({'url': instance.logo_url})
            html = Template(TEMPLATE).render(context)
            return html
        except ContestLogo.DoesNotExist:
            return ''
    return {'extra_menu_top_contestlogo': lazy(generator, unicode)()}
