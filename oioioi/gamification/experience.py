"""
Example usages:
1.

::

   Experience.add_experience_source(SubmissionsExperienceSource());
   Experience.add_experience_source(AchievementsExperienceSource());

2.

::

   experience = Experience(getUser("Olaf"));
   print experience.current_level
   experience.force_recalculate()
   print experience.current_level

3.

::

   experience2 = Experience(level=4, experience=300)

4.

::

  Experience.force_recalculate_all()
"""
import itertools
from math import floor
from django.contrib.auth.models import User
from django.db import transaction
from oioioi.contests.models import UserResultForProblem, ScoreReport
from oioioi.gamification.models import CachedExperienceSourceID,\
        CachedExperienceSourceTotal, ProblemDifficulty
import oioioi.gamification.constants as const


class Experience(object):
    """A class for (mostly) observing user gamification experience and levels.
       Provides basic functionality to actually calculate current experience,
       but the grunt of work should be done by ExperienceSource (see below).
    """

    def __init__(self, user=None, level=None, experience=None):
        """This class can be used either by providing a user or a
           level/experience pair, but not both.
           Since you can't recalculate anything for a pair, force_recalculate()
           will fail in that situation, throwing an ValueError exception.
           ValueError will be also thrown if both user and a pair are provided.

           For easier use of the class, if experience in the level/exp pair is
           overflowing to an another level, it will be fixed when accessing
           it by class properties (current_level, level_exp_tuple,
           current_experience).
        """
        self._user = None
        self._level = None
        self._experience = None

        if user is not None and (level is not None or experience is not None):
            raise ValueError("Can't provide both user and lvl/exp pair")

        if user is not None:
            self._user = user
        elif level is not None and experience is not None:
            needed = Experience.exp_to_lvl(level + 1)
            while needed <= experience:
                experience -= needed
                level += 1
                needed = Experience.exp_to_lvl(level + 1)
            self._experience = experience
            self._level = level
        else:
            raise ValueError("Only one argument in lvl/exp pair was provided")

    ######################
    # Inspection methods #
    ######################
    @property
    def level_exp_tuple(self):
        """Returns a tuple (current lvl, current exp on this lvl)"""
        if self._user is not None:
            return Experience._level_from_total_exp(self._get_experience_sum())
        return self._level, self._experience

    @property
    def current_level(self):
        lvl, _ = self.level_exp_tuple
        return lvl

    @property
    def current_experience(self):
        """Returns users current experience on current level, total experience
           of a user is not provided, it's an implementation detail and
           should be of no use whatsoever.
        """
        _, exp = self.level_exp_tuple
        return exp

    @property
    def required_experience_to_lvlup(self):
        """current_experience / required_experience_to_lvlup will give you a
           percentage to level up.
        """
        level, _ = self.level_exp_tuple
        return Experience.exp_to_lvl(level + 1)

    @staticmethod
    def exp_to_lvl(lvl):
        """Returns required experience to level up from level x-1 to x."""
        if lvl <= 0:
            raise ValueError("Can't calculate experience for levels <= 0")

        if lvl > const.SoftCapLevel:
            return floor((Experience.exp_to_lvl(const.SoftCapLevel) + (
                lvl - const.SoftCapLevel) * const.LinearMultiplier))
        return floor(const.ExpBase**(lvl-1) * const.ExpMultiplier)


    ################
    # Modificators #
    ################
    @staticmethod
    def add_experience_source(source):
        """Adds a global instance of your ExperienceSource, what it returns
           will be summed with other sources to give a total experience per
           user.
        """
        Experience._sources.append(source)

    @staticmethod
    def clear_experience_sources():
        """I just hope you know what you're doing."""
        Experience._sources = []

    def force_recalculate(self):
        """If you think there was a desync between a cache and expected
           experience, or maybe doing manual changes to the server -> you
           can do a recalculation of all the sources for one user.
        """
        if self._user is None:
            raise ValueError("Can't call force_recalculate without a user")

        for source in Experience._sources:
            source.force_recalculate(self._user)

    @staticmethod
    def force_recalculate_all():
        """Force experience calculation for ALL the users. Warning though,
           it might take a long time.
        """
        for source, current_user in itertools.product(
                Experience._sources, User.objects.all()
        ):
            source.force_recalculate(current_user)

    ############
    # Privates #
    ############

    _sources = []

    def _get_experience_sum(self):
        """Gets sum of all experience sources for user."""
        result = 0
        for source in Experience._sources:
            result += source.get_experience(self._user)
        return result

    @staticmethod
    def _level_from_total_exp(exp):
        """Returns a tuple (current lvl, exp on this lvl)."""
        current_lvl = 0
        required_exp_to_next = Experience.exp_to_lvl(1)
        while exp >= required_exp_to_next:
            exp -= required_exp_to_next
            current_lvl += 1
            required_exp_to_next = Experience.exp_to_lvl(current_lvl + 1)
        return current_lvl, exp


class ExperienceSource(object):
    """This class is some sort of source of experience for each user, be it
       their submissions or achievements, they should be implemented using this
       class, it's an interface I guess and doesn't need to be derived, it's
       here for information purposes, but both functions need to be
       implemented.
    """

    def get_experience(self, user):
        """This function is for reading only, and shouldn't change anything,
           returns current total experience for the user from this source.
        """
        raise NotImplementedError()

    def force_recalculate(self, user):
        """Clear all the cache for the user and regenerate his total
           experience, to actually get the result -> use get_experience(user).
        """
        raise NotImplementedError()


class DBCachedByKeyExperienceSource(ExperienceSource):
    """An abstract experience source that allows caching in database by some
       key. It's constructor takes a unique name (a string) which will be
       used to filter all cache rows, IDs should not repeat in the same
       unique name, but probably will with different unique names (eg.
       achievement no. 1 and programming problem no. 1). Derived classes
       should call this class functions.

       Also the names must be smaller than 50 chars

       transaction.atomic is used where possible (and sane) -> Sources might be
       called from not-in-transaction requests (such as doing
       force_recalculate_all() from shell).
    """

    #####################
    # Outside interface #
    #####################

    def __init__(self, name):
        self._name = name

    def get_experience(self, user):
        """This probably shouldn't be changed in derived classes, should work
           on its own.
        """
        try:
            return CachedExperienceSourceTotal.objects.get(
                name=self._name, user=user
            ).value
        except CachedExperienceSourceTotal.DoesNotExist:
            return 0

    def force_recalculate(self, user):
        """Clears the cache, add stuff to it yourself when deriving (and
        call the super)."""
        CachedExperienceSourceID.objects.filter(
            name=self._name, user=user
        ).delete()
        CachedExperienceSourceTotal.objects.filter(
            name=self._name, user=user
        ).delete()

    #############
    # Modifiers #
    #############

    def has_row(self, cache_id, user):
        return self._get_row(cache_id, user) is not None

    def get_value(self, cache_id, user):
        obj = self._get_row(cache_id, user)
        if obj is not None:
            return obj.value
        return 0

    def add_row(self, cache_id, user, value):
        with transaction.atomic():
            assert not CachedExperienceSourceID.objects.filter(
                name=self._name, user=user, cache_id=cache_id
            ).exists()

            new_obj = CachedExperienceSourceID(
                name=self._name, user=user, cache_id=cache_id, value=value
            )
            new_obj.save()
            self._modify_total(user, value)

    def del_row(self, cache_id, user):
        with transaction.atomic():
            old_obj = self._get_row(cache_id, user)
            assert old_obj is not None
            self._modify_total(user, -1 * old_obj.value)
            old_obj.delete()

    def set_value(self, cache_id, user, value):
        with transaction.atomic():
            self.del_row(cache_id, user)
            self.add_row(cache_id, user, value)

    ############
    # Privates #
    ############

    def _get_row(self, cache_id, user):
        try:
            return CachedExperienceSourceID.objects.get(
                name=self._name, cache_id=cache_id, user=user
            )
        except CachedExperienceSourceID.DoesNotExist:
            return None

    def _modify_total(self, user, how_much_add):
        try:
            total_obj = CachedExperienceSourceTotal.objects \
                .select_for_update().get(name=self._name, user=user)
        except CachedExperienceSourceTotal.DoesNotExist:
            total_obj = CachedExperienceSourceTotal(name=self._name,
                                                    user=user, value=0)
        total_obj.value += how_much_add
        total_obj.save()

        if total_obj.value == 0:
            total_obj.delete()


class ProblemExperienceSource(DBCachedByKeyExperienceSource):
    """The source of experience coming from completed problems."""
    def __init__(self):
        super(ProblemExperienceSource, self).__init__("ProblemSource")

    def force_recalculate(self, user):
        super(ProblemExperienceSource, self).force_recalculate(user)

        results = UserResultForProblem.objects.filter(
                    user=user,
                    problem_instance__contest__isnull=True
                ).select_related(
                    'submission_report',
                    'submission_report__submission',
                    'submission_report__submission'
                        '__problem_instance__problem__problemdifficulty'
                ).all()

        self._recalculate_results(results)

    def force_recalculate_problem(self, problem):
        results = UserResultForProblem.objects.filter(
                    problem_instance__problem=problem,
                    problem_instance__contest__isnull=True
                ).select_related(
                    'submission_report',
                    'submission_report__submission',
                    'submission_report__submission'
                        '__problem_instance__problem__problemdifficulty'
                ).all()

        self._recalculate_results(results)

    def handle_submission_report(self, submission_report):
        # Only score non-contest problems
        if submission_report.submission.problem_instance.contest is not None:
            return

        try:
            reward = submission_report.submission.problem\
                        .problemdifficulty.experience

            if reward == 0:
                return  # Difficulty was not set

            # Assumes there is only one ScoreReport for a SubmissionReport
            probleminstance_id =\
                submission_report.submission.problem_instance.pk
            user = submission_report.submission.user

            if user is None:
                return

            score_report = submission_report.scorereport_set.get()
            full_points = (score_report.score == score_report.max_score)

            if full_points:
                if self.has_row(probleminstance_id, user):
                    self.set_value(probleminstance_id, user, reward)
                else:
                    self.add_row(probleminstance_id, user, reward)

        except (ProblemDifficulty.DoesNotExist, ScoreReport.DoesNotExist):
            # This problem has no difficulty set or no score report, so ignore
            return

    def _recalculate_results(self, results):
        # Handle submissions
        for result in results:
            if result.submission_report is not None:
                self.handle_submission_report(result.submission_report)


PROBLEM_EXPERIENCE_SOURCE = ProblemExperienceSource()
Experience.add_experience_source(PROBLEM_EXPERIENCE_SOURCE)
