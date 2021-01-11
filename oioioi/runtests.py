import os
import sys

from django.conf import settings
from django.test.utils import get_runner

os.environ['DJANGO_SETTINGS_MODULE'] = 'oioioi.test_settings'
test_dir = os.path.join(os.path.dirname(__file__), '..')[0]
sys.path.insert(0, test_dir)


def runtests():
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True)
    failures = test_runner.run_tests([])
    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests()
