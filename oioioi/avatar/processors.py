from django.utils.functional import lazy
from django_gravatar.helpers import get_gravatar_url

def gravatar(request):
    if request.user.is_authenticated():
        def generator():
            return unicode(get_gravatar_url(request.user.email, size=25)) or ''
        return {'avatar': lazy(generator, unicode)()}
    else:
        return {}
