from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from oioioi.default_settings import INSTALLATION_CONFIG_VERSION

GITHUB_LINK = "https://github.com/sio2project/oioioi/" \
        "#changes-in-the-deployment-directory"


def version_check():
    deployment_config_version = getattr(settings, 'CONFIG_VERSION', 0)
    if deployment_config_version != INSTALLATION_CONFIG_VERSION:
        raise ImproperlyConfigured(_("Your deployment config version "
                "(%(deployment_version)s) does not match the config version "
                "(%(version)s) of your OIOIOI installation. Please "
                "consult %(href)s for the list of "
                "changes in the deployment directory.") %
                {
                    'deployment_version': deployment_config_version,
                    'version': INSTALLATION_CONFIG_VERSION,
                    'href': GITHUB_LINK,
                })
