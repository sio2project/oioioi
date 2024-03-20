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

        # The round starts at 2011.07.31-20:57:58
        def get_time(hour):
            return datetime(2011, 7, 31, hour, 0, 0, tzinfo=timezone.utc)

        # Published before the round start
        tp = TestsPackage(
            problem=problem,
            name='tp1',
            description='some desc',
            publish_date=get_time(19),
        )
        tp.full_clean()
        tp.save()
        tp.tests.add(test1, test2)

        # Published after the round start
        tp2 = TestsPackage(
            problem=problem,
            name='tp2',
            description='some desc2',
            publish_date=get_time(22),
        )
        tp2.full_clean()
        tp2.save()
        tp2.tests.add(test2)

        # Never published
        tp3 = TestsPackage(
            problem=problem,
            name='tp3',
            description='some desc3',
            publish_date=None,
        )
        tp3.full_clean()
        tp3.save()
        tp3.tests.add(test1)

        def check_accessibility(id, visible):
            url = reverse('test', kwargs={
                'contest_id': contest.id,
                'package_id': id,
            })
            self.assertEqual(visible, 200 == self.client.get(url).status_code)

        def check_visibility(visible, invisible):
            list_url = reverse('contest_files', kwargs={'contest_id': contest.id})

            self.assertTrue(self.client.login(username='test_user'))
            response = self.client.get(list_url)
            self.assertEqual(200, response.status_code)
            for i in visible:
                self.assertContains(response, i.name + '.zip')
                check_accessibility(i.id, True)
            for i in invisible:
                self.assertNotContains(response, i.name + '.zip')
                check_accessibility(i.id, False)
            for f in response.context['files']:
                self.assertEqual(f['admin_only'], False)

            self.assertTrue(self.client.login(username='test_admin'))
            response = self.client.get(list_url)
            self.assertEqual(200, response.status_code)
            for i in visible + invisible:
                self.assertContains(response, i.name + '.zip')
                check_accessibility(i.id, True)
            invisible_names = set([i.name + '.zip' for i in invisible])
            for f in response.context['files']:
                self.assertEqual(f['admin_only'], f['name'] in invisible_names)

        # Now, so after everything
        check_visibility([tp, tp2], [tp3])
        # Before everything
        with fake_time(get_time(18)):
            check_visibility([], [tp, tp2, tp3])
        # After the first publish_date, but before the round start
        with fake_time(get_time(20)):
            check_visibility([], [tp, tp2, tp3])
        # After the round start, but before the second publish_date
        with fake_time(get_time(21)):
            check_visibility([tp], [tp2, tp3])
        # After everything
        with fake_time(get_time(23)):
            check_visibility([tp, tp2], [tp3])
