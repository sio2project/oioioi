# pylint: disable=unused-import
# Important. This import is to register signal handlers. Do not remove it.
import oioioi.base.signal_handlers

from oioioi.base.config_version_check import version_check

# Check if deployment and installation config versions match
version_check()
