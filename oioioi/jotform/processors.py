from django.conf import settings
from django.template import Context
from django.template.loader import render_to_string

def jotform(request):
    if settings.JOTFORM_ID:
        return {'extra_head_jotform':
                render_to_string('jotform/jotform_head.html',
                    Context({'jotform_id': settings.JOTFORM_ID}))}
    else:
        return {}
