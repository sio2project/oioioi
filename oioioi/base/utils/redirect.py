from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.http import is_safe_url
from django import VERSION as DJANGO_VERSION


def safe_redirect(request, url, fallback='index'):
    if DJANGO_VERSION >= (1, 11):
        if url and is_safe_url(url=url, allowed_hosts=request.get_host()):
            next_page = url
        else:
            next_page = reverse(fallback)
    else:
        if url and is_safe_url(url=url, host=request.get_host()):
            next_page = url
        else:
            next_page = reverse(fallback)

    return redirect(next_page)
