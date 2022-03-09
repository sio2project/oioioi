from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect(request, url, fallback='index'):
    if url and url_has_allowed_host_and_scheme(url=url, allowed_hosts=request.get_host()):
        next_page = url
    else:
        next_page = reverse(fallback)
    return redirect(next_page)
