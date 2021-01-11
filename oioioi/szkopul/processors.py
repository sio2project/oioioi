import six
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.functional import lazy


def szkopul_contact(request):
    if settings.SZKOPUL_SUPPORT_EMAIL:

        def generator():
            return render_to_string(
                'szkopul/contact-info.html',
                request=request,
                context={'support_email': settings.SZKOPUL_SUPPORT_EMAIL},
            )

        return {'extra_body_szkopul_contact': lazy(generator, six.text_type)()}
    else:
        return {}
