from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404

from oioioi.filetracker.utils import stream_file
from oioioi.problems.utils import can_admin_problem_instance
from oioioi.quizzes.models import QuizAnswerPicture, QuizQuestionPicture


def picture_view(request, mode, picture_id):
    modes = {
        "a": QuizAnswerPicture,
        "q": QuizQuestionPicture,
    }
    if mode not in modes:
        return HttpResponseNotFound()
    picture = get_object_or_404(modes[mode], id=picture_id)
    if not any(
        pi.controller.can_submit(request, pi) or can_admin_problem_instance(request, pi)
        for pi in picture.quiz.probleminstance_set.filter(contest=request.contest)
    ):
        raise PermissionDenied
    return stream_file(picture.file)
