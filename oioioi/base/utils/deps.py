from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def is_django_app_installed(app_name):
    return app_name in settings.INSTALLED_APPS


def check_django_app_dependencies(app_name, depends_on, strict=False):
    if app_name.endswith(".models"):
        app_name = app_name[:-7]
    if not is_django_app_installed(app_name):
        raise ImproperlyConfigured(
            "Django app %s is loaded (because something depends on it), but it's not in settings.INSTALLED_APPS. Please add it there." % (app_name,)
        )
    index = settings.INSTALLED_APPS.index(app_name)
    assert isinstance(depends_on, (list, tuple))
    for dep in depends_on:
        if not is_django_app_installed(dep):
            raise ImproperlyConfigured("Django app %s requires %s, which is not present in settings.INSTALLED_APPS" % (app_name, dep))
        if strict and index > settings.INSTALLED_APPS.index(dep):
            raise ImproperlyConfigured(
                "Django app %(overriding)s overrides "
                "%(overridden)s, so %(overriding)s should be placed "
                "before %(overridden)s in settings.INSTALLED_APPS" % {"overriding": app_name, "overridden": dep}
            )
