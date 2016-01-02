from django.conf import settings
from django.utils.importlib import import_module

# pylint: disable=unused-import
# Important. This import is to register signal handlers. Do not remove it.
import oioioi.base.signal_handlers
from oioioi.base.config_version_check import version_check

# Check if deployment and installation config versions match
version_check()

for app in settings.INSTALLED_APPS:
    if app.startswith('oioioi.'):
        try:
            # Controllers should be imported at startup, because they register
            # mixins
            import_module(app + '.controllers')
        except ImportError:
            pass
