from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

from oioioi.default_settings import INSTALLATION_CONFIG_VERSION

GITHUB_LINK = "https://github.com/sio2project/oioioi/blob/master/UPGRADING.rst#changes-in-the-deployment-directory"


def setup_check():
    deployment_config_version = getattr(settings, 'CONFIG_VERSION', 0)
    if deployment_config_version == 0:
        return

    if deployment_config_version != INSTALLATION_CONFIG_VERSION:
        raise ImproperlyConfigured(
            _(
                "The 'CONFIG_VERSION' in your custom "
                "deployment directory (%(deployment_version)s) does not match "
                "the 'INSTALLATION_CONFIG_VERSION' (%(version)s) in "
                "'default_settings.py'. Please consult %(href)s for the list "
                "of changes in the deployment directory."
            )
            % {
                'deployment_version': deployment_config_version,
                'version': INSTALLATION_CONFIG_VERSION,
                'href': GITHUB_LINK,
            }
        )
    databases = getattr(settings, 'DATABASES', {})
    if not all(database.get('ATOMIC_REQUESTS') for database in databases.values()):
        raise ImproperlyConfigured(
            "'ATOMIC_REQUESTS' in database settings should always be set to True."
        )
