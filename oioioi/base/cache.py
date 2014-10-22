import os
import os.path
import errno

from django.core.cache.backends.filebased import FileBasedCache

# FileBasedCache in Django < 1.7 creates the cache folder with
# default permissions. This is insecure, especially that our
# default configuration places the cache in /tmp.
#
# This may be removed once we migrate to Django >= 1.7.


class DefaultCache(FileBasedCache):
    def _createdir(self):
        if not os.path.exists(self._dir):
            try:
                os.makedirs(self._dir, 0o700)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise EnvironmentError(
                        "Cache directory '%s' does not exist "
                        "and could not be created'" % self._dir)
