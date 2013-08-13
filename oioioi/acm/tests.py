from django.test import TestCase
from oioioi.contests.models import Contest

# The following tests use full-contest fixture, which may be changed this way:
# 1. Create new database, do syncdb and migrate
# 2. ./manage.py loaddata acm_test_full_contest.json
# 3. Login as 'test_admin' with password 'a'
# 4. Modify something (use Time Admin and User Switching)
# 5. ./manage.py dumpdata --format json --indent 2 --all > some_file.json
# 6. Copy ``some_file`` to acm/fixtures/acm_test_full_contest.json


class TestACMRanking(TestCase):
    fixtures = ['acm_test_full_contest']

    def test_fixture(self):
        self.assertTrue(Contest.objects.exists())
        self.assertEqual(Contest.objects.get().controller_name,
                'oioioi.acm.controllers.ACMContestController')
