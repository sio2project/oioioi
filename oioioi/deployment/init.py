import os
import sys


def init_env(settings_dir):
    sys.path.insert(0, settings_dir)
    if os.environ.get('PYTHONPATH'):
        os.environ['PYTHONPATH'] = settings_dir + ':' + os.environ['PYTHONPATH']
    else:
        os.environ['PYTHONPATH'] = settings_dir
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
