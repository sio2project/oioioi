from django.test import TestCase
from django.core.urlresolvers import reverse
from oioioi.base.tests import check_not_accessible
from oioioi.contests.models import Submission, ProblemInstance, Contest
from oioioi.programs.models import Test, ModelSolution
from oioioi.sinolpack.tests import get_test_filename
from django.utils.html import strip_tags, escape

# Don't Repeat Yourself.
# Serves for both TestProgramsViews and TestProgramsXssViews
def extract_code(show_response):
    # Current version of pygments generates two <pre> tags,
    # first for line numeration, second for code.
    preFirst = show_response.content.find('</pre>') + 6
    preStart = show_response.content.find('<pre>', preFirst) + 5
    preEnd = show_response.content.find('</pre>', preFirst)
    # Get substring and strip tags.
    show_response.content = strip_tags(
        show_response.content[preStart:preEnd]
    )

class TestProgramsViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission']

    def test_submission_views(self):
        self.client.login(username='test_user')
        submission = Submission.objects.get()
        kwargs = {'contest_id': submission.problem_instance.contest.id,
                'submission_id': submission.id}
        # Download shown response.
        show_response = self.client.get(reverse('show_submission_source',
            kwargs=kwargs))
        self.assertEqual(show_response.status_code, 200)
        # Download plain text response.
        download_response = self.client.get(reverse(
            'download_submission_source', kwargs=kwargs))
        # Extract code from <pre>'s
        extract_code(show_response)
        # Shown code has entities like &gt; - let's escape the plaintext.
        download_response.content = escape(download_response.content)
        # Now it should work.
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(show_response.content, download_response.content)
        self.assertIn('main()', show_response.content)
        self.assertTrue(show_response.content.strip().endswith('}'))
        self.assertTrue(download_response['Content-Disposition'].startswith(
            'attachment'))

    def test_test_views(self):
        self.client.login(username='test_admin')
        test = Test.objects.get(name='0')
        kwargs = {'test_id': test.id}
        response = self.client.get(reverse('download_input_file',
            kwargs=kwargs))
        self.assertEqual(response.content.strip(), '1 2')
        response = self.client.get(reverse('download_output_file',
            kwargs=kwargs))
        self.assertEqual(response.content.strip(), '3')

    def test_submissions_permissions(self):
        submission = Submission.objects.get()
        test = Test.objects.get(name='0')
        for view in ['show_submission_source', 'download_submission_source']:
            check_not_accessible(self, view, kwargs={
                'contest_id': submission.problem_instance.contest.id,
                'submission_id': submission.id})
        for view in ['download_input_file', 'download_output_file']:
            check_not_accessible(self, view, kwargs={'test_id': test.id})
        self.client.login(user='test_user')
        for view in ['download_input_file', 'download_output_file']:
            check_not_accessible(self, view, kwargs={'test_id': test.id})

    def test_model_solutions_view(self):
        pi = ProblemInstance.objects.get()
        ModelSolution.objects.recreate_model_submissions(pi)
        url = reverse('oioioiadmin:contests_probleminstance_models',
                args=(pi.id,))
        self.client.login(username='test_admin')
        response = self.client.get(url)
        for element in ['>sum<', '>sum1<', '>sumb0<', '>sums1<', '>100<',
                '>0<']:
            self.assertIn(element, response.content)
        self.assertEqual(response.content.count('subm_status subm_OK'), 8)
        self.assertEqual(response.content.count('subm_status subm_WA'), 6)
        self.assertEqual(response.content.count('subm_status subm_CE'), 2)
        self.assertEqual(response.content.count('>10.00s<'), 5)

class TestProgramsXssViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission_xss']

    def test_submission_xss_views(self):
        self.client.login(username='test_user')
        submission = Submission.objects.get()
        kwargs = {'contest_id': submission.problem_instance.contest.id,
                'submission_id': submission.id}
        # Download shown response.
        show_response = self.client.get(reverse('show_submission_source',
            kwargs=kwargs))
        self.assertEqual(show_response.status_code, 200)
        # Download plain text response.
        download_response = self.client.get(reverse(
            'download_submission_source', kwargs=kwargs))
        # Extract code from <pre>'s
        extract_code(show_response)
        # Shown code has entities like &gt; - let's escape the plaintext.
        download_response.content = escape(download_response.content)
        # Now it should work.
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(show_response.content, download_response.content)
        self.assertEqual(show_response.content.find('<script>'), -1)
        self.assertEqual(download_response.content.find('<script>'), -1)
        self.assertIn('main()', show_response.content)
        self.assertTrue(show_response.content.strip().endswith('}'))
        self.assertTrue(download_response['Content-Disposition'].startswith(
            'attachment'))

class TestSubmissionAdmin(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission']

    def test_submissions_changelist(self):
        self.client.login(username='test_admin')
        pi = ProblemInstance.objects.get()
        ModelSolution.objects.recreate_model_submissions(pi)
        url = reverse('oioioiadmin:contests_submission_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('(sum.c)', response.content)
        self.assertIn('test_user', response.content)
        self.assertIn('subm_status subm_OK', response.content)

class TestSubmittingAsAdmin(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def test_ignored_submission(self):
        self.client.login(username='test_user')
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        url = reverse('submit', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('IGNORED', response.content)

        self.client.login(username='test_admin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('IGNORED', response.content)

        data = {
            'problem_instance_id': pi.id,
            'file': open(get_test_filename('sum-various-results.cpp'), 'rb'),
            'user': 'test_user',
            'kind': 'IGNORED'
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 1)
        submission = Submission.objects.get()
        self.assertEqual(submission.user.username, 'test_user')
        self.assertEqual(submission.kind, 'IGNORED')

        url = reverse('default_ranking', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Test User', response.content)

        self.client.login(username='test_user')
        url = reverse('my_submissions', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('(Ignored)', response.content)
