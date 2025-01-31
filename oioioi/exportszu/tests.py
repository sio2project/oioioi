import os.path
import shutil
import tarfile
import tempfile

from django.core.management import call_command
from io import BytesIO

from oioioi.base.tests import TestCase
from oioioi.contests.models import Contest, Round
from oioioi.exportszu.utils import SubmissionsWithUserDataCollector
from oioioi.programs.models import ProgramSubmission


class TestSubmissionsWithUserDataCollector(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_extra_rounds',
    ]

    def assert_correct_submission_data(self, submission_data_list):
        for s in submission_data_list:
            submission = ProgramSubmission.objects.get(id=s.submission_id)
            self.assertEqual(s.user_id, submission.user_id)
            self.assertEqual(s.username, submission.user.username)
            self.assertEqual(s.first_name, submission.user.first_name)
            self.assertEqual(s.last_name, submission.user.last_name)
            self.assertEqual(
                s.problem_short_name, submission.problem_instance.short_name
            )

            # there is no registration so None is expected
            self.assertIsNone(s.school)
            self.assertIsNone(s.school_city)
            self.assertIsNone(s.city)

            self.assertEqual(
                s.solution_language, os.path.splitext(s.source_file.name)[1][1:]
            )
            self.assertIsNotNone(s.source_file)

    def test_default(self):
        contest = Contest.objects.get(id="c")
        collector = SubmissionsWithUserDataCollector(contest)
        submission_data_list = collector.collect_list()
        submissions = [s.submission_id for s in submission_data_list]
        self.assertEqual(submissions, [1, 2, 3, 4])
        self.assert_correct_submission_data(submission_data_list)

    def test_not_only_final(self):
        contest = Contest.objects.get(id="c")
        collector = SubmissionsWithUserDataCollector(contest, only_final=False)
        submission_data_list = collector.collect_list()
        submissions = [s.submission_id for s in submission_data_list]
        # actually all are final
        self.assertEqual(submissions, [1, 2, 3, 4])
        self.assert_correct_submission_data(submission_data_list)

    def test_specific_round(self):
        contest = Contest.objects.get(id="c")
        round = Round.objects.get(id=3)
        collector = SubmissionsWithUserDataCollector(contest, round=round)
        submission_data_list = collector.collect_list()
        submissions = [s.submission_id for s in submission_data_list]
        self.assertEqual(submissions, [3])
        self.assert_correct_submission_data(submission_data_list)


class TestFinalSubmissionsWithUserDataCollector(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_another_submission',
    ]

    def test_default(self):
        contest = Contest.objects.get(id="c")
        collector = SubmissionsWithUserDataCollector(contest)
        submission_data_list = collector.collect_list()
        submissions = [s.submission_id for s in submission_data_list]
        self.assertEqual(submissions, [1])

    def test_not_only_final(self):
        contest = Contest.objects.get(id="c")
        collector = SubmissionsWithUserDataCollector(contest, only_final=False)
        submission_data_list = collector.collect_list()
        submissions = [s.submission_id for s in submission_data_list]
        self.assertEqual(submissions, [1, 2])


class TestBestScoreIsFinalSubmissionsWithUserDataCollector(TestCase):
    fixtures = [
        'test_users',
        'test_contest_best_score_is_final',
        'test_full_package',
        'test_problem_instance',
        'test_submissions_best_score_is_final',
    ]

    def test_default(self):
        contest = Contest.objects.get(id="c")
        collector = SubmissionsWithUserDataCollector(contest)
        submission_data_list = collector.collect_list()
        submissions = [s.submission_id for s in submission_data_list]
        self.assertEqual(submissions, [2])

    def test_not_only_final(self):
        contest = Contest.objects.get(id="c")
        collector = SubmissionsWithUserDataCollector(contest, only_final=False)
        submission_data_list = collector.collect_list()
        submissions = [s.submission_id for s in submission_data_list]
        self.assertEqual(submissions, [1, 2])


INDEX_HEADER = (
    'submission_id,user_id,username,first_name,last_name,city,'
    'school,school_city,problem_short_name,score\r\n'
)


class TestExportCommand(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_another_submission',
    ]

    def test_export(self):
        tmpdir = tempfile.mkdtemp()
        try:
            archive_path = os.path.join(tmpdir, 'archive.tgz')
            call_command('export_submissions', 'c', archive_path)
            archive = tarfile.open(archive_path, 'r:gz')
            index = archive.extractfile('c/INDEX').read()
            self.assertEqual(
                index.decode(),
                INDEX_HEADER + "1,1001,test_user,Test,User,NULL,NULL,NULL,zad1,34\r\n",
            )
            files = sorted([member.name for member in archive.getmembers()])
            self.assertEqual(files, ["c", "c/1:test_user:zad1.cpp", "c/INDEX"])
        finally:
            shutil.rmtree(tmpdir)


class TestExportSubmissionsView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_link_to(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get('/c/c/dashboard/')
        self.assertInHTML(
            '<a class="list-group-item list-group-item-action " href="/c/c/export_submissions/">\n'
            'Export submissions\n</a>',
            response.content.decode('utf-8'),
        )

    def test_download(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get('/c/c/export_submissions/')
        self.assertContains(response, 'round')
        self.assertContains(response, 'final')
        response = self.client.post(
            '/c/c/export_submissions/', {'round': '', 'only_final': 'on'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Disposition'], 'attachment; filename="c.tgz"'
        )
        result_file = BytesIO(b''.join(response.streaming_content))
        with tarfile.open(fileobj=result_file, mode='r:gz') as tar:
            file_list = sorted([member.name for member in tar.getmembers()])
            self.assertEqual(file_list, ['c', 'c/1:test_user:zad1.cpp', 'c/INDEX'])
            index = tar.extractfile('c/INDEX').read()
            self.assertEqual(
                index.decode(),
                INDEX_HEADER + '1,1001,test_user,Test,User,NULL,NULL,NULL,zad1,34\r\n',
            )
            submission = tar.extractfile('c/1:test_user:zad1.cpp').read()
            self.assertRegex(submission, b'.*int main.*')
