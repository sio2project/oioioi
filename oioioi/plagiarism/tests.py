import six
from django.core.management import call_command
from django.core.management.base import CommandError
from mock import Mock, patch

from oioioi.base.tests import TestCase
from oioioi.plagiarism.utils import MossClient, MossException

SAMPLE_RESULTS_URL = "http://moss.stanford.edu/results/10/123456789"
ALWAYS_OK_SUBMIT = Mock(return_value=SAMPLE_RESULTS_URL)


class TestMossClient(TestCase):
    @patch(
        'oioioi.plagiarism.utils.MossClient.HOSTNAME',
        'nonexistent.subdomain.moss.stanford.edu',
    )
    def test_connection_refused(self):
        client = MossClient(userid=1234, lang="C++")
        with self.assertRaisesRegex(MossException, 'Could not connect'):
            client.submit()

    def test_moss_query_rejection(self):
        # create a socket which always receives "no"
        mock_socket = Mock()
        mock_socket_ctor = Mock(return_value=mock_socket)
        mock_recv = Mock(return_value=six.ensure_binary("no\n"))
        mock_socket.recv = mock_recv

        with patch('socket.socket', mock_socket_ctor):
            client = MossClient(userid=1234, lang="C++")
            with self.assertRaisesRegex(MossException, 'rejected .* query'):
                client.submit()


class TestMossSubmitCommand(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_another_submission',
    ]

    @patch('oioioi.plagiarism.utils.MossClient.submit', ALWAYS_OK_SUBMIT)
    def test_export(self):
        call_command('moss_submit', 1, '-a', '-l=C++', '-i=1234')

    @patch('oioioi.plagiarism.utils.MossClient.submit', ALWAYS_OK_SUBMIT)
    def test_no_submissions(self):
        with self.assertRaisesRegex(CommandError, 'no submissions'):
            call_command('moss_submit', 1, '-a', '-l=Pascal', '-i=1234')

    @patch('oioioi.plagiarism.utils.MossClient.submit', ALWAYS_OK_SUBMIT)
    def test_adding_files(self):
        with patch('oioioi.plagiarism.utils.MossClient.add_file') as mock_add_file:
            call_command('moss_submit', 1, '-a', '-l=C++', '-i=1234')
        self.assertEqual(mock_add_file.call_count, 2)

        display_names = {call_args[0][1] for call_args in mock_add_file.call_args_list}
        self.assertEqual(display_names, {"TU1001_1", "TU1001_2"})


class TestMossSubmitView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    MOSS_SUBMIT_URL = '/c/c/moss_submit/'

    def test_admin_menu_link(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get('/c/c/dashboard/')
        self.assertContains(response, self.MOSS_SUBMIT_URL)

    @patch('oioioi.plagiarism.utils.MossClient.submit', ALWAYS_OK_SUBMIT)
    def test_submit(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(self.MOSS_SUBMIT_URL)
        self.assertContains(response, 'language')
        self.assertContains(response, 'problem_instance')
        self.assertContains(response, 'only_final')
        self.assertContains(response, 'userid')
        self.assertContains(response, 'submit')
        response = self.client.post(
            self.MOSS_SUBMIT_URL,
            {
                'problem_instance': '1',
                'language': 'C++',
                'userid': '1234',
                'only_final': 'on',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, SAMPLE_RESULTS_URL)
