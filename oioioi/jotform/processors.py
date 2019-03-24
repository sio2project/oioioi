import six
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.functional import lazy


def jotform(request):
    if settings.JOTFORM_ID:
        def generator():
            return render_to_string('jotform/jotform-head.html',
                                    request=request,
                                    context={'jotform_id': settings.JOTFORM_ID})
        return {'extra_head_jotform': lazy(generator, six.text_type)()}
    else:
        return {}
