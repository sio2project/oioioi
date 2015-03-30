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
        pass

    ######################
    # Inspection methods #
    ######################
    @property
    def current_level(self):
        pass

    @property
    def current_experience(self):
        """
        Returns users current experience on current level, total experience of a
        user is not provided, it's an implementation detail and should be of no
        use whatsoever
        """
        pass

    @property
    def required_experience_to_lvlup(self):
        """
        current_experience / required_experience_to_lvlup will give you a
        percentage to level up
        """
        pass

    ################
    # Modificators #
    ################
    @staticmethod
    def add_experience_source(source):
        """
        Adds a global instance of your ExperienceSource, what it returns will be
        summed with other sources to give a total experience per user
        """
        pass

    def force_recalculate(self):
        """
        If you think there was a desync between a cache and expected experience,
        or maybe doing manual changes to the server -> you can do a
        recalculation of all the sources for one user
        """
        pass

    @staticmethod
    def force_recalculate_all():
        """
        Force experience calculation for ALL the users. Warning though,
        it might take a long time
        """
        pass


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
        pass

    def force_recalculate(self, user):
        """
        Clear all the cache for the user and regenerate his total
        experience, to actually get the result -> use get_experience(user)
        """
        pass