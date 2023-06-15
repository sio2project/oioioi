import os.path
from datetime import datetime, timezone

from django.test import RequestFactory
from django.urls import reverse

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import (
    Contest,
    ProblemInstance,
    ScoreReport,
    SubmissionReport,
)
from oioioi.contests.tests import SubmitMixin
from oioioi.problems.models import Problem
from oioioi.quizzes import views
from oioioi.quizzes.models import (
    QuestionReport,
    Quiz,
    QuizAnswer,
    QuizAnswerPicture,
    QuizQuestion,
    QuizQuestionPicture,
    QuizSubmission,
)


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
            post_data.update(
                {'quiz_' + str(problem_instance.id) + '_q_' + str(qid): answers[qid]}
            )

        response = self.client.post(url, post_data)

        return response


class TestTextInput(TestCase, SubmitQuizMixin):
    fixtures = [
        'test_users',
        'test_basic_contest',
        'test_problem_instance',
        'test_quiz_problem_with_text_input',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))

    def test_simple_submission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)

        response = self.submit_quiz(
            contest,
            problem_instance,
            {
                '1': 'Answer - correct',
                '2': 'A',
            },
        )
        self._assertSubmitted(contest, response)

        submission = QuizSubmission.objects.get()
        controller = submission.problem_instance.controller

        controller.judge(submission)
        submission_report = SubmissionReport.objects.get(
            submission=submission, status="ACTIVE"
        )
        self.assertEqual(submission_report.score_report.score, 50)
        report = SubmissionReport.objects.filter(
            submission=submission, status='ACTIVE', kind='NORMAL'
        ).get()
        score_report = ScoreReport.objects.get(submission_report=report)
        submission.status = score_report.status
        submission.score = score_report.score
        submission.max_score = score_report.max_score

    def test_second_possible_answer(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)

        response = self.submit_quiz(
            contest,
            problem_instance,
            {
                '1': 'Answer - correct',
                '2': 'B',
            },
        )
        self._assertSubmitted(contest, response)

        submission = QuizSubmission.objects.get()
        controller = submission.problem_instance.controller

        controller.judge(submission)
        submission_report = SubmissionReport.objects.get(
            submission=submission, status="ACTIVE"
        )
        self.assertEqual(submission_report.score_report.score, 50)

    def test_wrong_answer(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)

        response = self.submit_quiz(
            contest,
            problem_instance,
            {
                '1': 'Answer - wrong',
                '2': 'something completely incorrect',
            },
        )
        self._assertSubmitted(contest, response)

        submission = QuizSubmission.objects.get()
        controller = submission.problem_instance.controller

        controller.judge(submission)
        submission_report = SubmissionReport.objects.get(
            submission=submission, status="ACTIVE"
        )
        self.assertEqual(submission_report.score_report.score, 0)


class TestSubmission(TestCase, SubmitQuizMixin):
    fixtures = [
        'test_users',
        'test_basic_contest',
        'test_quiz_problem',
        'test_quiz_problem_second',
        'test_problem_instance',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))

    def test_simple_submission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)

        response = self.submit_quiz(
            contest, problem_instance, {'1': '1', '2': ('3', '4')}
        )
        self._assertSubmitted(contest, response)

    def test_empty_multiple_choice(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)

        response = self.submit_quiz(contest, problem_instance, {'1': '1', '2': ()})
        self._assertSubmitted(contest, response)

    def test_wrong_id(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)

        response = self.submit_quiz(
            contest,
            problem_instance,
            {'1': '3', '2': ()},  # answer 3 belongs to question 2
        )
        self.assertContains(response, "Select a valid choice")

        response = self.submit_quiz(
            contest,
            problem_instance,
            {'1': '1337', '2': ()},  # such an answer doesn't exist
        )
        self.assertContains(response, "Select a valid choice")

    def test_submission_unanswered_question(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)

        response = self.submit_quiz(
            contest,
            problem_instance,
            {'1': '', '2': ()},  # single-choice questions must have some answer
        )
        self.assertContains(response, "Answer is required")


class TestScore(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_quiz_problem',
        'test_quiz_problem_second',
        'test_problem_instance',
        'test_quiz_submission',
    ]

    def test_multiple_choice_no_correct_answer_score(self):
        submission = QuizSubmission.objects.get(pk=1)
        controller = submission.problem_instance.controller

        controller.judge(submission)
        submission_report = SubmissionReport.objects.get(
            submission=submission, status="ACTIVE"
        )
        question_report = QuestionReport.objects.get(
            question=3, submission_report=submission_report
        )

        self.assertEqual(question_report.score, 27)

    def test_all_answers_correct_score(self):
        submission = QuizSubmission.objects.get(pk=1)
        controller = submission.problem_instance.controller

        controller.judge(submission)
        submission_report = SubmissionReport.objects.get(
            submission=submission, status="ACTIVE"
        )
        question_report = QuestionReport.objects.get(
            question=1, submission_report=submission_report
        )

        self.assertEqual(question_report.score, 27)

    def test_one_answer_incorrect_score(self):
        submission = QuizSubmission.objects.get(pk=1)
        controller = submission.problem_instance.controller

        controller.judge(submission)
        submission_report = SubmissionReport.objects.get(
            submission=submission, status="ACTIVE"
        )
        question_report = QuestionReport.objects.get(
            question=2, submission_report=submission_report
        )

        self.assertEqual(question_report.score, 0)


# Inherits from TestScore class in order to run all tests from parent class after adding
# new questions to a quiz to check if adding new questions does not break judging the old ones.
class TestScoreRejudgeAfterNewQuestionsAdded(TestScore):
    def setUp(self):
        self.quiz = Quiz.objects.get(pk=1)
        self.submission = QuizSubmission.objects.get(pk=1)
        self.controller = self.submission.problem_instance.controller

        self.closed_added_question = QuizQuestion.objects.create(
            quiz=self.quiz, question='First added question'
        )
        QuizAnswer.objects.create(
            question=self.closed_added_question,
            answer='Only correct answer',
            is_correct=True,
        )

        self.open_added_question = QuizQuestion.objects.create(
            question='Second added question', quiz=self.quiz, is_text_input=True
        )
        QuizAnswer.objects.create(
            question=self.open_added_question,
            answer='Only correct text answer',
            is_correct=True,
        )

    def test_closed_added_question_no_given_answer_score(self):
        self.controller.judge(self.submission)
        submission_report = SubmissionReport.objects.get(
            submission=self.submission, status="ACTIVE"
        )
        question_report = QuestionReport.objects.filter(
            question=self.closed_added_question, submission_report=submission_report
        )

        self.assertFalse(question_report.exists())

    def test_open_added_question_no_given_answer_score(self):
        self.controller.judge(self.submission)
        submission_report = SubmissionReport.objects.get(
            submission=self.submission, status="ACTIVE"
        )
        question_report = QuestionReport.objects.filter(
            question=self.open_added_question, submission_report=submission_report
        )

        self.assertFalse(question_report.exists())


class TestSubmissionView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_quiz_problem',
        'test_problem_instance',
        'test_quiz_submission',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))

    def test_question_report(self):
        contest = Contest.objects.get()
        submission = QuizSubmission.objects.get(pk=1)
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        response = self.client.get(reverse('submission', kwargs=kwargs))

        self.assertContains(response, '27 / 27', count=1)
        self.assertContains(response, '0 / 27', count=1)

    def test_submission_score_visible(self):
        submission = QuizSubmission.objects.get(pk=1)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }
        expected_score = 50
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertContains(response, '<td>{}</td>'.format(expected_score), html=True)

    def test_diff_submission_unavailable(self):
        submission = QuizSubmission.objects.get(pk=1)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertNotContains(response, "Diff submissions")


class TestEditQuizQuestions(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_quiz_problem']

    def setUp(self):
        self.assertTrue(
            self.client.login(username='test_user')
        )  # this user is not an admin

    def test_edit_quiz_questions(self):
        # test_user is an author of this problem
        problem = Problem.objects.get(pk=1)
        url = reverse('oioioiadmin:quizzes_quiz_change', args=[problem.pk])
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Add another Quiz Question')


class TestQuizBleach(TestCase):
    fixtures = [
        'test_users',
        'test_basic_contest',
        'test_quiz_bleach',
        'test_problem_instance',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))

    def test_quizbleach(self):
        response = self.client.get(
            reverse('submit', kwargs={'contest_id': Contest.objects.get().id})
        )
        self.assertContains(response, '<pre>Answer - correct</pre>')
        self.assertNotContains(
            response, '<script src="http://weaselcrow.com/keylogger.js"></script>'
        )


class TestPictures(TestCase):
    fixtures = [
        'test_users',
        'test_basic_contest',
        'test_quiz_problem_pictures',
        'test_problem_instance',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))

    def test_embedding(self):
        response = self.client.get(
            reverse('submit', kwargs={'contest_id': Contest.objects.get().id})
        )

        def test(picture):
            self.assertContains(response, picture.get_absolute_url())

        test(QuizQuestionPicture.objects.get())
        test(QuizAnswerPicture.objects.get())

    def test_invalid_mode(self):
        response = views.picture_view(RequestFactory().request(), 'z', 1)
        self.assertEqual(response.status_code, 404)

    def test_access(self):
        url = QuizQuestionPicture.objects.get().get_absolute_url()
        with fake_time(datetime(1999, 1, 1, tzinfo=timezone.utc)):
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 403)

    def test_download(self):
        cat_path = os.path.join(os.path.dirname(__file__), 'files', 'cat.jpg')
        picture = QuizQuestionPicture.objects.get()
        picture.file.save('cat', open(cat_path, 'rb'))
        picture.save()
        response = self.client.get(picture.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.streaming)
        self.assertEqual(
            b''.join(response.streaming_content), open(cat_path, 'rb').read()
        )


class TestQuizProblemView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_problem_site',
        'test_quiz_problem_second',
        'test_problem_site_second',
    ]

    disabled_quiz_tabs = ['Problem statement']
    allowed_quiz_tabs = ['Secret key', 'Settings']

    def test_quiz_tab_visibility(self):
        self.assertTrue(self.client.login(username='test_admin'))
        quiz = Quiz.objects.get(pk=101)
        url = reverse('problem_site', kwargs={'site_key': quiz.problemsite.url_key})
        response = self.client.get(url, follow=True)

        for (allowed_tab, disabled_tab) in zip(
            self.allowed_quiz_tabs, self.disabled_quiz_tabs
        ):
            self.assertContains(response, allowed_tab)
            self.assertNotContains(response, disabled_tab)

    def test_normal_problem_tab_visibility(self):
        self.assertTrue(self.client.login(username='test_admin'))
        problem = Problem.objects.get(pk=1)
        url = reverse('problem_site', kwargs={'site_key': problem.problemsite.url_key})
        response = self.client.get(url, follow=True)

        for tab_name in self.allowed_quiz_tabs + self.disabled_quiz_tabs:
            self.assertContains(response, tab_name)
