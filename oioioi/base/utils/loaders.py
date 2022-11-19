from importlib import import_module

from django.conf import settings


def load_modules(module_name):
    """This function loads module_name.py files in all installed apps."""
    for app_module in list(settings.INSTALLED_APPS):
        try:
            module = '%s.%s' % (app_module, module_name)
            import_module(module)
        except ImportError:
            continue
