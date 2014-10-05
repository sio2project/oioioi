from oioioi.base.utils import multiton
from oioioi.base.utils import group_cache
from oioioi.base.utils.file_lock import FileLock


@multiton
class CacheGenerator(object):
    """This class is a thread-safe way to retrieve data that was cached
       using group_cache. With CacheGenerator, when data is not present
       in the cache, only one thread is delegated to update it. The
       rest of the threads wait on file locks, thereby reducing the
       server load.

       .. note::

           :class:`CacheGenerator` should be used to retrieve data
           from group_cache. That being said, it is safe to invalidate
           group_cache without thread synchronisation.

       .. note::

           :class:`CacheGenerator` is a context manager, so it should
           be used in a ``with`` statement.
    """
    def __init__(self, cache_key, cache_group):
        self.cache_key = cache_key
        self.cache_group = cache_group
        self.name = self.get_instance_name(cache_key, cache_group)
        self.lock = None

        self._in_context = 0

    def __enter__(self):
        self._in_context += 1
        if self._in_context == 1:
            self.lock = FileLock(self.name)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._in_context -= 1
        if self._in_context == 0:
            self.lock.unlock()

    @staticmethod
    def get_instance_name(cache_key, cache_group):
        return group_cache.generate_cache_key(cache_key, cache_group)

    def _get_obj_from_cache(self):
        return group_cache.get(self.cache_key, self.cache_group)

    def _cache_obj(self, obj, timeout):
        group_cache.set(self.cache_key, self.cache_group, obj, timeout)

    def get_cached_obj(self, generate_obj, timeout):
        """:param generate_obj: A function taking no arguments and
                                returning a current version of the
                                object to cache.
           :param timeout: Timeout in seconds for the cached object.
        """
        self.lock.lock_shared()

        cached_obj = self._get_obj_from_cache()

        if cached_obj is not None:
            # Object is in the cache, so we return it and *maintain*
            # the lock for the lifetime of this object.
            return cached_obj

        self.lock.unlock()
        self.lock.lock_exclusive()

        # After acquiring an exclusive lock we check if the object is
        # still missing from the cache.
        cached_obj = self._get_obj_from_cache()

        if cached_obj is not None:
            self.lock.lock_shared()
            return cached_obj

        try:
            cached_obj = generate_obj()
            self._cache_obj(cached_obj, timeout)
        except:
            self.lock.unlock()
            raise

        self.lock.lock_shared()
        return cached_obj
