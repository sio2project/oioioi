import itertools
from math import floor
from django.contrib.auth.models import User
from models import CachedExperienceSourceID, CachedExperienceSourceTotal
import constants as const

"""
Example usage
Experience.add_experience_source(SubmissionsExperienceSource());
Experience.add_experience_source(AchievementsExperienceSource());

experience = Experience(getUser("Olaf"));
print experience.current_level
experience.force_recalculate(getUser("Tomek"))
print experience.current_level

Experience.force_recalculate_all()
"""

class Experience(object):
    """
    A class for (mostly) observing user gamification experience and levels.
    Provides basic functionality to actually calculate current experience,
    but the grunt of work should be done by ExperienceSource (see below).
    """

    def __init__(self, user):
        """
        This class is expected to be used per-user basis,
        so it accepts a user object, but also a username will work
        """
        self._user = user

    ######################
    # Inspection methods #
    ######################
    @property
    def level_exp_tuple(self):
        """Returns a tuple (current lvl, current exp on this lvl)"""
        return Experience._level_from_total_exp(self._get_experience_sum())

    @property
    def current_level(self):
        lvl, _ = self.level_exp_tuple
        return lvl

    @property
    def current_experience(self):
        """
        Returns users current experience on current level, total experience of a
        user is not provided, it's an implementation detail and should be of no
        use whatsoever
        """
        _, exp = self.level_exp_tuple
        return exp

    @property
    def required_experience_to_lvlup(self):
        """
        current_experience / required_experience_to_lvlup will give you a
        percentage to level up
        """
        level, _ = self.level_exp_tuple
        return Experience.exp_to_lvl(level + 1)

    @staticmethod
    def exp_to_lvl(lvl):
        """Returns required experience to level up from level x-1 to x"""
        if lvl <= 0:
            return 0

        if lvl > const.SoftCapLevel:
            return floor((Experience.exp_to_lvl(const.SoftCapLevel) + (
                lvl - const.SoftCapLevel) * const.LinearMultiplier))
        return floor(const.ExpBase**(lvl-1) * const.ExpMultiplier)


    ################
    # Modificators #
    ################
    @staticmethod
    def add_experience_source(source):
        """
        Adds a global instance of your ExperienceSource, what it returns will be
        summed with other sources to give a total experience per user
        """
        Experience._sources.append(source)

    @staticmethod
    def clear_experience_sources():
        """I just hope you know what you're doing"""
        Experience._sources = []

    def force_recalculate(self):
        """
        If you think there was a desync between a cache and expected experience,
        or maybe doing manual changes to the server -> you can do a
        recalculation of all the sources for one user
        """
        for source in Experience._sources:
            source.force_recalculate(self._user)

    @staticmethod
    def force_recalculate_all():
        """
        Force experience calculation for ALL the users. Warning though,
        it might take a long time
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
        """Gets sum of all experience sources for user"""
        result = 0
        for source in Experience._sources:
            result += source.get_experience(self._user)
        return result

    @staticmethod
    def _level_from_total_exp(exp):
        """Returns a tuple (current lvl, exp on this lvl)"""
        current_lvl = 0
        required_exp_to_next = Experience.exp_to_lvl(1)
        while exp >= required_exp_to_next:
            exp -= required_exp_to_next
            current_lvl += 1
            required_exp_to_next = Experience.exp_to_lvl(current_lvl + 1)
        return current_lvl, exp


class ExperienceSource(object):
    """
    This class is some sort of source of experience for each user, be it
    their submissions or achievements, they should be implemented using this
    class, it's an interface I guess and doesn't need to be derived, it's here
    for information purposes, but both functions need to be implemented.
    """

    def get_experience(self, user):
        """
        This function is for reading only, and shouldn't change anything,
        returns current total experience for the user from this source
        """
        raise NotImplementedError()

    def force_recalculate(self, user):
        """
        Clear all the cache for the user and regenerate his total
        experience, to actually get the result -> use get_experience(user)
        """
        raise NotImplementedError()

class DBCachedByKeyExperienceSource(ExperienceSource):
    """
    An abstract experience source that allows caching in database by some key
    It's constructor takes a unique name (a string) which will be used to filter
    all cache rows, IDs should not repeat in the same unique name, but probably
    will with different unique names (eg. achievement no. 1 and programming
    problem no. 1)
    Derived classes should call this class functions

    Also the names must be smaller than 50 chars
    """

    #####################
    # Outside interface #
    #####################

    def __init__(self, name):
        self._name = name

    def get_experience(self, user):
        """
        This probably shouldn't be changed in derived classes, should work on
        its own
        """
        try:
            return CachedExperienceSourceTotal.objects.get(
                name=self._name, user=user
            ).value
        except CachedExperienceSourceTotal.DoesNotExist:
            return 0

    def force_recalculate(self, user):
        """Clears the cache, add stuff to it yourself when deriving"""
        CachedExperienceSourceID.objects.filter(
            name=self._name, user=user
        ).delete()
        CachedExperienceSourceTotal.objects.filter(
            name=self._name, user=user
        ).delete()

    #############
    # Modifiers #
    #############

    def get_value(self, cache_id, user):
        obj = self._get_row(cache_id, user)
        if obj is not None:
            return obj.value
        return 0

    def add_row(self, cache_id, user, value):
        assert not CachedExperienceSourceID.objects.filter(
            name=self._name, user=user, cache_id=cache_id
        ).exists()

        new_obj = CachedExperienceSourceID(
            name=self._name, user=user, cache_id=cache_id, value=value
        )
        new_obj.save()
        self._modify_total(user, value)

    def del_row(self, cache_id, user):
        old_obj = self._get_row(cache_id, user)
        assert old_obj is not None
        self._modify_total(user, -1 * old_obj.value)
        old_obj.delete()


    def set_value(self, cache_id, user, value):
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
            total_obj = CachedExperienceSourceTotal.objects.get(
                name=self._name, user=user
            )
        except CachedExperienceSourceTotal.DoesNotExist:
            total_obj = CachedExperienceSourceTotal(name=self._name,
                                                    user=user, value=0)
        total_obj.value += how_much_add
        total_obj.save()

        if total_obj.value == 0:
            total_obj.delete()