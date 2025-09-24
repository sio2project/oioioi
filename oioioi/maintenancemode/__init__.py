from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# If redirect url hasn't been specified we treat it as
# ImproperlyConfigured
if not hasattr(settings, "MAINTENANCE_MODE_REDIRECT_URL"):
    raise ImproperlyConfigured("URL for maintenance mode has not been provided")
