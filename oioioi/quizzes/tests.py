from django.core.urlresolvers import reverse

from oioioi.base.tests import TestCase
from oioioi.contests.models import ProblemInstance, Contest
from oioioi.contests.tests import SubmitMixin


class SubmitQuizMixin(SubmitMixin):
    def submit_quiz(self, contest, problem_instance, answers):
        """
        Submits a quiz with given answer
        :param contest: in what contest to submit
        :param problem_instance: indicates which quiz to submit
        :param answers: dictionary mapping question ids to:
                        1) answer id
                        2) list of answer ids if question is multiple choice
        :return response to the request
        """
        url = reverse('submit', kwargs={'contest_id': contest.id})

        post_data = {
            'problem_instance_id': problem_instance.id,
        }

        for qid in answers:
            post_data.update({
                'quiz_' + str(problem_instance.id) + '_q_' + str(qid):
                    answers[qid]
            })

        return self.client.post(url, post_data)


class TestSubmission(TestCase, SubmitQuizMixin):
    fixtures = ['test_users', 'test_basic_contest', 'test_quiz_problem',
                'test_quiz_problem_second', 'test_problem_instance']

    def setUp(self):
        self.client.login(username='test_user')

    def test_simple_submission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)

        response = self.submit_quiz(contest, problem_instance, {
            '1': '1',
            '2': ('3', '4')
        })
        self._assertSubmitted(contest, response)

    def test_empty_multiple_choice(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)

        response = self.submit_quiz(contest, problem_instance, {
            '1': '1',
            '2': ()
        })
        self._assertSubmitted(contest, response)

    def test_wrong_id(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)

        response = self.submit_quiz(contest, problem_instance, {
            '1': '3',  # answer 3 belongs to question 2
            '2': ()
        })
        self.assertContains(response, "Select a valid choice")

        response = self.submit_quiz(contest, problem_instance, {
            '1': '1337',  # such an answer doesn't exist
            '2': ()
        })
        self.assertContains(response, "Select a valid choice")

    def test_submission_unanswered_question(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)

        response = self.submit_quiz(contest, problem_instance, {
            '1': '',  # single-choice questions must have some answer
            '2': ()
        })
        self.assertContains(response, "Answer is required")
