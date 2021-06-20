from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import is_safe_url


def safe_redirect(request, url, fallback='index'):
    if url and is_safe_url(url=url, allowed_hosts=request.get_host()):
        next_page = url
    else:
        next_page = reverse(fallback)
    return redirect(next_page)
