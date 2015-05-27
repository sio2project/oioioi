from django.forms.fields import BooleanField
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from oioioi.base.utils import ObjectWithMixins
from oioioi.gamification.friends import UserFriends
from oioioi.gamification.models import CodeSharingSettings
from oioioi.base.preferences import PreferencesSaved, PreferencesFactory
from oioioi.contests.controllers import ContestController
from oioioi.contests.models import Submission, SubmissionReport
from oioioi.problems.models import Problem
from oioioi.programs.controllers import ProgrammingContestController, \
    ProgrammingProblemController
from oioioi.gamification.constants import CODE_SHARING_FRIENDS_ENABLED,\
    CODE_SHARING_PREFERENCES_DEFAULT, SuggestLvl2From, SuggestLvl3From, \
    SuggestLvl4From, SuggestLvl5From
from oioioi.problems.controllers import ProblemController
from oioioi.gamification.experience import Experience, \
    PROBLEM_EXPERIENCE_SOURCE
from oioioi.gamification.difficulty import _update_problem_difficulty,\
    get_problems_by_difficulty, DIFFICULTY

class CodeSharingController(ObjectWithMixins):
    """When viewing a programming problem, we want to compare our code with our
       friends. This class provides api for actually getting access permissions
       and a list of visible codes for us. If in the future we want to have
       different permissions for accessing code than just friends,
       this controller can be extended with mixins.
       Actually implementing friends-based permissions are done in other
       class - this is because we might not want to use friends at all and
       skip that.
    """

    def can_see_code(self, task, user_requester, user_sharing):
        """This function returns a bool indicating whether the requester can
           see code of sharer for the task.
        """
        return False

    def shared_with_me(self, task, user):
        """This function returns a queryset of all the possible codes the
           user can see for the provided task.
        """
        all_shared = self.all_shared_with_me(user)
        return all_shared.filter(
            submissionreport__userresultforproblem__problem_instance__problem=
                task
        )

    def all_shared_with_me(self, user):
        """This function returns a queryset of all the possible codes the
           user can see.
        """
        return Submission.objects.none()


class CodeSharingFriendsController(ObjectWithMixins):
    """Code sharing is allowed for friends who set the required field in
       preferences.
    """

    @staticmethod
    def set_up():
        def preferences_value_callback(field_name, user):
            return CodeSharingSettings.objects.sharing_allowed(user)

        @transaction.atomic
        def on_preferences_saved(sender, **kwargs):
            obj, created = CodeSharingSettings.get_or_create(
                user=sender.user
            )
            obj.code_share_allowed = sender.cleaned_data['code_sharing']
            obj.save()

        CodeSharingController.mix_in(CodeSharingFriendsController)
        PreferencesFactory.add_field(
            'code_sharing',
            BooleanField,
            preferences_value_callback,
            label=_("Whether to allow your friends to see your problem "
                    "solutions"),
            required=False
        )
        PreferencesSaved.connect(on_preferences_saved)

    def can_see_code(self, task, user_requester, user_sharing):
        if not UserFriends(user_requester).is_friends_with(user_sharing):
            return False
        return (CodeSharingSettings.objects.sharing_allowed(user_sharing) and
                self._has_submission(task, user_sharing))

    def all_shared_with_me(self, user):
        allowed_sharing = UserFriends(user).friends
        if CODE_SHARING_PREFERENCES_DEFAULT is True:
            allowed_sharing = allowed_sharing.exclude(
                codesharingsettings__code_share_allowed=False
            )
        else:  # is False
            allowed_sharing = allowed_sharing.filter(
                codesharingsettings__code_share_allowed=True
            )
        result = Submission.objects.filter(
            submissionreport__userresultforproblem__user__in=allowed_sharing
        )
        return result

    def _has_submission(self, task, user):
        return Submission.objects.filter(
            problem_instance__problem=task,
            user=user
        ).exists()

if CODE_SHARING_FRIENDS_ENABLED:
    CodeSharingFriendsController.set_up()


class CodeSharingProgramControllerMixin(object):
    """A mixin allowing users to see shared submissions' contents.
    """
    def can_see_source(self, request, submission):
        prev = super(CodeSharingProgramControllerMixin, self) \
                .can_see_source(request, submission)

        return prev or CodeSharingController().can_see_code(
                submission.problem, request.user, submission.user)

ProgrammingProblemController.mix_in(CodeSharingProgramControllerMixin)


class CodeSharingContestControllerMixin(object):
    """A mixin allowing users to see shared submissions' contents.
    """
    def filter_visible_sources(self, request, queryset):
        prev = super(CodeSharingContestControllerMixin, self) \
                .filter_visible_sources(request, queryset)

        if not request.user.is_authenticated():
            return prev

        shared = CodeSharingController().all_shared_with_me(request.user)
        return prev | queryset.filter(id__in=shared)


ProgrammingContestController.mix_in(CodeSharingContestControllerMixin)


class ProblemExperienceMixinForContestController(object):
    """A helper mixin for oioioi.gamification.ProblemExperienceSource."""
    def submission_judged(self, submission, rejudged=False):
        super(ProblemExperienceMixinForContestController, self)\
                .submission_judged(submission, rejudged)

        try:
            report = SubmissionReport.objects.get(
                userresultforproblem__user=submission.user,
                userresultforproblem__problem_instance=
                    submission.problem_instance
            )

            PROBLEM_EXPERIENCE_SOURCE.handle_submission_report(report)

        except SubmissionReport.DoesNotExist:
            pass  # Possible in tests

ContestController.mix_in(ProblemExperienceMixinForContestController)


class TaskSuggestionController(ObjectWithMixins):
    """Since we're collecting some data about the user we can somehow suggest a
       task for him to complete on theirs learning level, this controller is
       the API. To provide your implementation you should mix-in with this
       class and override suggest_task which should return a suggested problem
       for the user. You might want to also call super and do something with
       the task you got from a mixed-in object higher in hierarchy, but it's
       not required

       Warning though, this controller might return None if no task is
       suggested eg. no tasks in the database
    """

    def suggest_task(self, user):
        """Returns a problem object as a suggestion for the user or None if no
           suggestion can be returned
        """
        user_level = Experience(user).current_level

        if user_level >= SuggestLvl5From:
            qset = get_problems_by_difficulty(DIFFICULTY.IMPOSSIBLE)
        elif user_level >= SuggestLvl4From:
            qset = get_problems_by_difficulty(DIFFICULTY.HARD)
        elif user_level >= SuggestLvl3From:
            qset = get_problems_by_difficulty(DIFFICULTY.MEDIUM)
        elif user_level >= SuggestLvl2From:
            qset = get_problems_by_difficulty(DIFFICULTY.EASY)
        else:
            qset = get_problems_by_difficulty(DIFFICULTY.TRIVIAL)

        try:
            return qset.filter(is_public=True).order_by('?').first()
        except Problem.DoesNotExist:
            return None


class DifficultyProblemMixin(object):
    """A class to mix-in with problem controller, overriding fill_ev
       to update difficulty rows"""
    def adjust_problem(self):
        """Creates row with difficulty for current problem"""
        super(DifficultyProblemMixin, self).adjust_problem()
        _update_problem_difficulty(self.problem)

ProblemController.mix_in(DifficultyProblemMixin)
