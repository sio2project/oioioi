from django.core.urlresolvers import get_script_prefix

def base_url(request):
    return {'base_url': get_script_prefix()}
