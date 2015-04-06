from django.test import TestCase
from django.contrib.auth.models import User
from experience import DBCachedByKeyExperienceSource, Experience,\
    ExperienceSource
from constants import ExpMultiplier, ExpBase, SoftCapLevel, LinearMultiplier


class TestExperienceModule(TestCase):
    fixtures = ['test_users.json']

    def test_caching_experience_source(self):
        test_user = User.objects.get(username='test_user')
        test_user1 = User.objects.get(username='test_user2')
        source = DBCachedByKeyExperienceSource('test_name')
        source.force_recalculate(test_user)

        source.add_row(0, test_user,  0)
        source.del_row(0, test_user)

        source.add_row(1, test_user1, 5)
        source.add_row(2, test_user1, 4)

        self.assertEquals(source.get_value(1, test_user1), 5)
        self.assertEquals(source.get_value(1, test_user),  0)
        self.assertEquals(source.get_experience(test_user),  0)
        self.assertEquals(source.get_experience(test_user1), 9)

        with self.assertRaises(AssertionError):
            source.set_value(3, test_user, 3)
        source.add_row(3, test_user, 3)
        source.set_value(2, test_user1, 3)

        self.assertEquals(source.get_value(1, test_user),  0)
        self.assertEquals(source.get_value(3, test_user),  3)
        self.assertEquals(source.get_value(2, test_user1), 3)
        self.assertEquals(source.get_value(1, test_user1), 5)
        self.assertEquals(source.get_experience(test_user), 3)
        self.assertEquals(source.get_experience(test_user1), 8)

        source.del_row(3, test_user)
        # Since the class doesn't do any actual logic at all, this SHOULD reset
        # everything to 0, it's the derivers responsibility to do something
        # sane
        source.force_recalculate(test_user1)

        self.assertEquals(source.get_experience(test_user),  0)
        self.assertEquals(source.get_experience(test_user1), 0)

    def test_experience_basic(self):
        # Yeah I guess not that much testing can be done here
        self.assertEquals(Experience.exp_to_lvl(-1), 0)
        self.assertEquals(Experience.exp_to_lvl(0), 0)
        self.assertEquals(Experience.exp_to_lvl(1), ExpMultiplier)
        self.assertEquals(Experience.exp_to_lvl(2), ExpBase*ExpMultiplier)
        self.assertEquals(
            Experience.exp_to_lvl(SoftCapLevel + 1),
            Experience.exp_to_lvl(SoftCapLevel) + LinearMultiplier
        )

    def test_experience_with_sources(self):
        class TestSource(ExperienceSource):
            """
            This class simulates desync with real experience, initially
            get_experience() returns one value, but after force_recalculate()
            return totally different one
            """
            def __init__(self, initial, after_recalc):
                self.value = initial
                self.recalc = after_recalc

            def get_experience(self, user):
                return self.value

            def force_recalculate(self, user):
                self.value = self.recalc

        # To level up to lvl 1 you need the ExpMultiplier experience
        test_source = TestSource(1, ExpMultiplier)
        test_source1 = TestSource(3, 1)
        try:
            Experience.add_experience_source(test_source)
            Experience.add_experience_source(test_source1)

            test_user = User.objects.get(username='test_user')

            exp = Experience(test_user)

            self.assertEquals(exp.current_experience, 4)
            self.assertEquals(exp.current_level, 0)
            self.assertEquals(
                exp.required_experience_to_lvlup,
                ExpMultiplier
            )
            self.assertEquals(exp.level_exp_tuple, (0, 4))

            exp.force_recalculate()

            self.assertEquals(exp.current_experience, 1)
            self.assertEquals(exp.current_level, 1)
            self.assertEquals(
                exp.required_experience_to_lvlup,
                ExpBase*ExpMultiplier
            )
            self.assertEquals(exp.level_exp_tuple, (1, 1))

            Experience.clear_experience_sources()

            self.assertEquals(exp.level_exp_tuple, (0, 0))

        finally:
            Experience.clear_experience_sources()

    def test_softcap(self):
        class ConstSource(ExperienceSource):
            """
            This source always returns the same value
            """
            def __init__(self, value):
                self.value = value

            def get_experience(self, user):
                return self.value

            def force_recalculate(self, user):
                pass

        def total_exp_to_lvl(level):
            total = 0
            for i in xrange(1, level + 1):
                total += Experience.exp_to_lvl(i)
            return total

        try:
            Experience.add_experience_source(
                ConstSource(total_exp_to_lvl(SoftCapLevel))
            )

            test_user = User.objects.get(username='test_user')

            exp = Experience(test_user)

            self.assertEquals(exp.current_level, SoftCapLevel)
            self.assertEquals(
                exp.required_experience_to_lvlup,
                Experience.exp_to_lvl(SoftCapLevel) + LinearMultiplier
            )

            Experience.add_experience_source(
                ConstSource(Experience.exp_to_lvl((SoftCapLevel + 1)))
            )

            self.assertEquals(
                exp.required_experience_to_lvlup,
                Experience.exp_to_lvl(SoftCapLevel) + 2*LinearMultiplier
            )

        finally:
            Experience.clear_experience_sources()