import logging

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.memcached import PyLibMCCache

logger = logging.getLogger(__name__)


class FaultTolerantPyLibMCCache(PyLibMCCache):
    """PyLibMCCache that treats an unreachable memcached as a cache miss.

    The stock backend raises on connection errors, so a memcached restart
    turns every request touching the cache (including sessions with
    ``cached_db``) into an error 500. Here reads return the default, writes
    are dropped and the caller falls back to the database.
    ``incr`` and ``decr`` still raise, because callers rely on their result.
    """

    def _call(self, method, default, *args, **kwargs):
        try:
            return getattr(super(), method)(*args, **kwargs)
        except self._lib.Error:
            logger.warning("memcached %s failed", method, exc_info=True)
            return default

    def get(self, key, default=None, version=None):
        return self._call("get", default, key, default, version)

    def get_many(self, keys, version=None):
        return self._call("get_many", {}, keys, version)

    def has_key(self, key, version=None):
        return self._call("has_key", False, key, version)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        return self._call("add", False, key, value, timeout, version)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        return self._call("set", None, key, value, timeout, version)

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        return self._call("set_many", list(data), data, timeout, version)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        return self._call("touch", False, key, timeout, version)

    def delete(self, key, version=None):
        return self._call("delete", False, key, version)

    def delete_many(self, keys, version=None):
        return self._call("delete_many", None, keys, version)
