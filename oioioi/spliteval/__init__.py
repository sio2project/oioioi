from django.conf import settings

# SioworkersdBackend handles postponing checking by using priorities
if settings.SIOWORKERS_BACKEND == 'oioioi.sioworkers.backends.Sioworkersd\
        Backend' and settings.ENABLE_SPLITEVAL:
    raise AssertionError(
        "Please set ENABLE_SPLITEVAL to False when using Sioworkersd")
