import hashlib

from django.core.cache import cache

# This cache wrapper should be used when you have multiple items
# in cache that are somehow related and you want to be able to
# invalidate all of them at once.

# FIXME: Django 1.5 does not support caching forever.
GROUP_CACHE_INF = 29 * 24 * 60 * 60


def generate_cache_key(key, group):
    """Generates a cache key for a group item.

       :param key: The key of the cached item.
       :param group: The name of the group.
    """
    cache.add(group, 1, GROUP_CACHE_INF)

    key_fragments = [(group, cache.get(group)), ('KEY', key)]
    combined_key = ":".join(['%s-%s' % (name, value) for name, value in
                             key_fragments])

    return hashlib.md5(combined_key).hexdigest()


def invalidate(group):
    """Invalidates an entire group.

       :param group: The name of the group to invalidate.
    """
    if cache.get(group) is not None:
        cache.incr(group)


def set(key, group, value, timeout):
    """Generates a cache key for a group item.

       :param key: The key of the item to cache.
       :param group: The name of the group.
       :param value: The value that will be placed in the cache.
       :param timeout: Timeout in seconds for the cached value.
    """
    combined_key = generate_cache_key(key, group)
    cache.set(combined_key, value, timeout)


def get(key, group):
    """Generates a cache key for a group item.

       :param key: The key of the item to cache.
       :param group: The name of the group.
    """
    combined_key = generate_cache_key(key, group)
    return cache.get(combined_key)
