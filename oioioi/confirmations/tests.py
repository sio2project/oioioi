import re

from django.contrib.auth.models import User
from django.core import mail

from oioioi.base.tests import TestCase
from oioioi.confirmations.utils import (
    ProofCorrupted,
    submission_receipt_proof,
    verify_submission_receipt_proof,
)
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.participants.models import Participant
from oioioi.programs.models import ProgramSubmission
from oioioi.programs.tests import SubmitFileMixin


class TestMetadataProving(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_another_submission',
    ]

    def test_valid_proof(self):
        submission = ProgramSubmission.objects.get(pk=1)
        _proof_data_orig, proof = submission_receipt_proof(submission)
        proof_data = verify_submission_receipt_proof(
            proof, submission.source_file.read()
        )

        self.assertEqual(proof_data['id'], submission.id)
        self.assertEqual(proof_data['date'], submission.date)

    def test_invalid_proof(self):
        submission = ProgramSubmission.objects.get(pk=1)
        _proof_data_orig, proof = submission_receipt_proof(submission)

        with self.assertRaises(ProofCorrupted):
            verify_submission_receipt_proof(proof, b'spam')

        submission2 = ProgramSubmission.objects.get(pk=2)
        _proof_data_orig2, proof2 = submission_receipt_proof(submission2)

        proof_tokens = proof.split(':')
        proof2_tokens = proof2.split(':')
        proof_tokens[0] = proof2_tokens[0]
        corrupted_proof = ':'.join(proof_tokens)
        with self.assertRaises(ProofCorrupted):
            verify_submission_receipt_proof(
                corrupted_proof, submission.source_file.read()
            )


class TestEmailReceipt(TestCase, SubmitFileMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.oi.controllers.OIContestController'
        contest.save()
        Participant(contest=contest, user=User.objects.get(username='test_user')).save()

    def test_sending_receipt(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get()
        self.assertTrue(self.client.login(username='test_user'))
        response = self.submit_file(contest, problem_instance, file_size=1337)
        self._assertSubmitted(contest, response)

        email = mail.outbox[0].message().as_string()
        del mail.outbox[0]
        self.assertIn("OIOIOI login: test_user", email)
        self.assertIn(f"Contest id: {contest.id}", email)
        self.assertIn(f"Problem: {problem_instance.short_name}", email)
        self.assertIn("Submissions to this task: 2", email)
        self.assertIn("1337 bytes", email)
        proof = re.search(
            r'--- BEGIN PROOF DATA ---(.*)--- END PROOF DATA ---', email, re.DOTALL
        )
        self.assertTrue(proof)
        verify_submission_receipt_proof(proof.group(1), b'a' * 1337)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.submit_file(
            contest, problem_instance, user='test_admin', kind='NORMAL'
        )
        self._assertSubmitted(contest, response)
        self.assertEqual(len(mail.outbox), 1)

    def test_not_sending_receipt(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get()
        self.assertTrue(self.client.login(username='test_admin'))

        response = self.submit_file(contest, problem_instance, user='test_user')
        self._assertSubmitted(contest, response)
        self.assertEqual(len(mail.outbox), 0)

        response = self.submit_file(
            contest, problem_instance, user='test_admin', kind='IGNORED'
        )
        self._assertSubmitted(contest, response)
        self.assertEqual(len(mail.outbox), 0)
