import os
import zipfile
from datetime import datetime, timezone  # pylint: disable=E0611

from django.core.exceptions import ValidationError
from django.urls import reverse

from oioioi.base.tests import TestCase, fake_time
from oioioi.base.utils import strip_num_or_hash
from oioioi.contests.models import Contest
from oioioi.problems.models import Problem
from oioioi.programs.models import Test
from oioioi.testspackages.models import TestsPackage


class TestTestsPackages(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def _assertTestsInPackage(self, tests, tp):
        zipf = zipfile.ZipFile(tp.package, 'r')
        for t in tests:
            for f in [t.input_file, t.output_file]:
                file_name = strip_num_or_hash(os.path.basename(f.file.name))
                content1 = zipf.open(file_name).read()
                content2 = f.file.file.read()
                self.assertEqual(content1, content2)
        zipf.close()

    def _assertTestsNotInPackage(self, tests, tp):
        zipf = zipfile.ZipFile(tp.package, 'r')
        for t in tests:
            for f in [t.input_file, t.output_file]:
                with self.assertRaises(KeyError):
                    file_name = strip_num_or_hash(os.path.basename(f.file.name))
                    zipf.open(file_name)
        zipf.close()

    def test_validating_packages(self):
        problem = Problem.objects.get()
        tp = TestsPackage(
            problem=problem,
            name='some name',
            description='some desc',
            publish_date=datetime(2012, 8, 5, 0, 11, tzinfo=timezone.utc),
        )

        with self.assertRaises(ValidationError):
            tp.full_clean()

        tp = TestsPackage(
            problem=problem,
            name='some_name',
            description='some desc',
            publish_date=datetime(2012, 8, 5, 0, 11, tzinfo=timezone.utc),
        )
        tp.full_clean()
        tp.save()

    def test_packing_packages(self):
        problem = Problem.objects.get()
        test1 = Test.objects.get(name='0')
        test2 = Test.objects.get(name='1a')
        test3 = Test.objects.get(name='1b')
        test4 = Test.objects.get(name='2')

        tp = TestsPackage(
            problem=problem,
            name='some_name',
            description='some desc',
            publish_date=datetime(2012, 8, 5, 0, 11, tzinfo=timezone.utc),
        )
        tp.save()
        tp.tests.add(test1, test3)

        tp = TestsPackage.objects.get(id=1)

        self._assertTestsInPackage([test1, test3], tp)
        self._assertTestsNotInPackage([test2, test4], tp)

    def test_packages_visibility(self):
        problem = Problem.objects.get()
        contest = Contest.objects.get()
        test1 = Test.objects.get(name='0')
        test2 = Test.objects.get(name='1a')

        tp = TestsPackage(
            problem=problem,
            name='some_name',
            description='some desc',
            publish_date=datetime(2012, 8, 5, 0, 11, tzinfo=timezone.utc),
        )
        tp.full_clean()
        tp.save()
        tp.tests.add(test1, test2)

        tp2 = TestsPackage(
            problem=problem,
            name='some_name2',
            description='some desc2',
            publish_date=datetime(2012, 8, 5, 1, 11, tzinfo=timezone.utc),
        )
        tp2.full_clean()
        tp2.save()
        tp2.tests.add(test2)

        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('contest_files', kwargs={'contest_id': contest.id})

        with fake_time(datetime(2012, 8, 5, 0, 10, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertNotContains(response, 'some_name.zip')
            self.assertNotContains(response, 'some_name2.zip')

        with fake_time(datetime(2012, 8, 5, 0, 12, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertContains(response, 'some_name.zip')
            self.assertNotContains(response, 'some_name2.zip')
            self.assertEqual(200, response.status_code)

        with fake_time(datetime(2012, 8, 5, 1, 12, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertContains(response, 'some_name.zip')
            self.assertContains(response, 'some_name2.zip')
            self.assertEqual(200, response.status_code)

        url = reverse('test', kwargs={'contest_id': contest.id, 'package_id': 1})

        with fake_time(datetime(2012, 8, 5, 0, 10, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertEqual(403, response.status_code)

        with fake_time(datetime(2012, 8, 5, 0, 12, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertEqual(200, response.status_code)
