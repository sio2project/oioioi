from django.shortcuts import redirect
from django.utils.http import is_safe_url
from django.core.urlresolvers import reverse

def safe_redirect(request, url, fallback='index'):
    if url and is_safe_url(url=url, host=request.get_host()):
        next_page = url
    else:
        next_page = reverse(fallback)

    return redirect(next_page)
