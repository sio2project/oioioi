from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured

# Code based on django.contrib.auth.middleware.RemoteUserMiddleware
class IpDnsAuthMiddleware(object):
    """Middleware for authentication based on user IP or DNS hostname."""

    def process_request(self, request):
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The IpDns user auth middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE_CLASSES setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the IpDnsAuthMiddleware class.")

        ip_addr = request.META.get('REMOTE_ADDR')
        dns_name = request.META.get('REMOTE_HOST')

        if dns_name == ip_addr:
            dns_name = None

        if not dns_name and not ip_addr:
            return

        user = auth.authenticate(ip_addr=ip_addr, dns_name=dns_name)
        if user:
            auth.login(request, user)

