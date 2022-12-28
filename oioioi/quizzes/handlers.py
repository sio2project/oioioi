from django.db import transaction

from oioioi.contests.models import ScoreReport, SubmissionReport
from oioioi.contests.scores import IntegerScore
from oioioi.quizzes.models import QuestionReport, QuizAnswer, QuizSubmission


@transaction.atomic
def score_quiz(env, **kwargs):
    is_rejudge = env['is_rejudge']
    submission = QuizSubmission.objects.get(id=env['submission_id'])
    quiz = submission.problem_instance.problem.quiz
    questions = quiz.controller.select_questions(
        submission.user, submission.problem_instance, submission
    )
    if is_rejudge:
        submission = QuizSubmission.objects.get(pk=submission)
    submission_report = _create_submission_report(submission)

    score = 0
    max_score = 0
    for question in questions:
        score_tmp, ignore_question = _score_question(
            submission, submission_report, question, submission.problem_instance
        )
        if not ignore_question:
            score += score_tmp
            max_score += question.points

    _create_score_report(max_score, score, submission_report)
    return env


def _match_text_input(question, user_input, answer, problem_instance):
    user_input = user_input.strip()
    answer = answer.strip()
    if problem_instance.controller.is_quiz_question_answer_case_ignored(question):
        user_input = user_input.lower()
        answer = answer.lower()
    return user_input == answer


def _is_answer_correct(submitted_answer):
    return (
        submitted_answer.is_selected
        == QuizAnswer.objects.get(pk=submitted_answer.answer_id).is_correct
    )


def _create_score_report(max_score, score, submission_report):
    ScoreReport.objects.create(
        submission_report=submission_report,
        score=IntegerScore(score),
        status='OK',
        max_score=IntegerScore(max_score),
    )


def _create_submission_report(submission):
    submission_report = SubmissionReport.objects.create(
        submission=submission,
        status='ACTIVE',
        kind='NORMAL',
    )
    return submission_report


def _score_question(submission, submission_report, question, problem_instance):
    points = question.points
    question_report = QuestionReport(
        submission_report=submission_report,
        question=question,
        question_max_score=points,
        score=IntegerScore(0),
    )

    award_points = False
    ignore_question = True
    if question.is_text_input:
        text_answers = submission.quizsubmissiontextanswer_set.filter(question=question)
        if text_answers.exists():
            text_answer = text_answers.get().text_answer
            correct_answers = question.quizanswer_set.filter(is_correct=True)
            award_points = any(
                _match_text_input(
                    question, text_answer, answer.answer, problem_instance
                )
                for answer in correct_answers
            )
            ignore_question = False
    else:
        submitted_answers = submission.quizsubmissionanswer_set.filter(
            answer__question=question
        )
        if submitted_answers.exists():
            award_points = all(
                _is_answer_correct(answer) for answer in submitted_answers
            )
            ignore_question = False

    if not ignore_question:
        if award_points:
            question_report.score = IntegerScore(points)
            question_report.status = 'OK'
        question_report.save()

    return (points, ignore_question) if award_points else (0, ignore_question)
