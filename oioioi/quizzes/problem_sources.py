from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db import transaction
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.models import ProblemInstance
from oioioi.problems.problem_sources import ProblemSource
from oioioi.problems.utils import get_new_problem_instance
from oioioi.quizzes.forms import EmptyQuizSourceForm
from oioioi.quizzes.models import Quiz
from oioioi.base.utils import generate_key
from oioioi.problems.models import ProblemSite, Tag, TagThrough


class EmptyQuizSource(ProblemSource):
    key = 'emptyquiz_source'
    problem_controller_class = 'oioioi.quizzes.controllers.QuizProblemController'
    short_description = _("Add a quiz")

    def view(self, request, contest, existing_problem=None):
        is_reupload = existing_problem is not None
        if is_reupload:  # reuploading doesn't make much sense here
            return _("Reuploading quizzes is not supported")

        if request.method == "POST":
            form = EmptyQuizSourceForm(request.POST)
        else:
            form = EmptyQuizSourceForm()
        post_data = {'form': form, 'is_reupload': is_reupload}

        if request.method == "POST" and form.is_valid():
            with transaction.atomic():
                controller = self.problem_controller_class
                quiz = Quiz.objects.create(
                    name=form.cleaned_data['name'],
                    short_name=form.cleaned_data['short_name'],
                    controller_name=controller,
                    author=request.user
                )
                tag = Tag.objects.get_or_create(name='quiz')[0]
                TagThrough.objects.create(
                    problem=quiz,
                    tag=tag
                )
                ProblemSite.objects.create(
                    problem=quiz,
                    url_key=generate_key()
                )
                pi = ProblemInstance.objects.create(
                    problem=quiz,
                    short_name=quiz.short_name
                )
                quiz.main_problem_instance = pi
                quiz.save()
                if contest:
                    quiz.contest = contest
                    get_new_problem_instance(quiz, contest)

                messages.success(request, _("Quiz successfully added"))
                return safe_redirect(request, reverse(
                    'oioioiadmin:contests_probleminstance_changelist'))

        return TemplateResponse(request, "quizzes/emptyquiz-source.html",
                                post_data)
