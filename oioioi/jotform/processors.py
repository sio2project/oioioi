from django.conf import settings
from django.utils.functional import lazy
from django.template import RequestContext
from django.template.loader import render_to_string


def jotform(request):
    if settings.JOTFORM_ID:
        def generator():
            return render_to_string('jotform/jotform-head.html',
                context_instance=RequestContext(request,
                    {'jotform_id': settings.JOTFORM_ID}))
        return {'extra_head_jotform': lazy(generator, unicode)()}
    else:
        return {}
