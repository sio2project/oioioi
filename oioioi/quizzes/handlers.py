from oioioi.contests.models import ScoreReport, SubmissionReport
from oioioi.contests.scores import IntegerScore
from oioioi.quizzes.models import QuestionReport, QuizAnswer, QuizSubmission


def score_quiz(env, **kwargs):
    is_rejudge = env['is_rejudge']
    submission = QuizSubmission.objects.get(id=env['submission_id'])
    quiz = submission.problem_instance.problem.quiz
    questions = quiz.controller.select_questions(submission.user, submission.problem_instance, submission)
    score = 0
    max_score = 0
    if is_rejudge:
        submission = QuizSubmission.objects.get(pk=submission)

    submission_report = _create_submission_report(submission)

    for question in questions:
        score += _score_question(submission, submission_report,
                                      question)
        max_score += question.points

    _create_score_report(max_score, score, submission_report)
    return env


def _match_text_input(question, user_input, answer):
    if question.trim_whitespace:
        user_input = user_input.strip()
        answer = answer.strip()
    if question.ignore_case:
        user_input = user_input.lower()
        answer = answer.lower()
    return user_input == answer


def _is_answer_correct(submitted_answer):
    return submitted_answer.is_selected == QuizAnswer.objects.get(
        pk=submitted_answer.answer.id).is_correct


def _create_score_report(max_score, score, submission_report):
    ScoreReport.objects.create(
        submission_report=submission_report,
        score=IntegerScore(score),
        status='OK',
        max_score=IntegerScore(max_score)
    )


def _create_submission_report(submission):
    submission_report = SubmissionReport.objects.create(
        submission=submission,
        status='ACTIVE',
        kind='NORMAL',
    )
    return submission_report


def _score_question(submission, submission_report,
                    question):
    points = question.points
    question_report = QuestionReport(
        submission_report=submission_report,
        question=question,
        question_max_score=points,
        score=IntegerScore(0),
    )

    award_points = False
    if question.is_text_input:
        text_answer = submission.quizsubmissiontextanswer_set\
            .get(question=question).text_answer
        correct_answers = question.quizanswer_set.filter(is_correct=True)
        award_points = any(_match_text_input(question, text_answer, answer.answer)
                           for answer in correct_answers)
    else:
        submitted_answers = submission.quizsubmissionanswer_set\
            .filter(answer__question=question)
        award_points = all(_is_answer_correct(answer)
                           for answer in submitted_answers)

    if award_points:
        question_report.score = IntegerScore(points)
        question_report.status = 'OK'
        question_report.save()
        return points
    question_report.save()
    return 0
