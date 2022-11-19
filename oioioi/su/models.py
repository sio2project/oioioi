from django.contrib.auth.backends import ModelBackend
from django.utils.translation import gettext_lazy as _

# Modify django default backend to meet our needs
ModelBackend.supports_authentication = True
ModelBackend.description = _("Password authentication")
