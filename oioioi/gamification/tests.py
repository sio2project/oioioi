from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.dispatch import receiver
from oioioi.base.menu import OrderedRegistry
from oioioi.base.notification import NotificationHandler

from oioioi.gamification.experience import DBCachedByKeyExperienceSource, \
    Experience, ExperienceSource, ProblemExperienceSource, \
    PROBLEM_EXPERIENCE_SOURCE
from oioioi.gamification.constants import ExpMultiplier, ExpBase, \
    SoftCapLevel, LinearMultiplier, CODE_SHARING_FRIENDS_ENABLED,\
    CODE_SHARING_PREFERENCES_DEFAULT, Lvl1TaskExp
from oioioi.gamification.difficulty import DIFFICULTY, get_problem_difficulty,\
    get_problems_by_difficulty, parse_old_problems
from oioioi.gamification.friends import UserFriends, FriendshipRequest,\
    FriendshipRequestSent, FriendshipRequestAccepted,\
    FriendshipRequestRefused, FriendshipEnded
from oioioi.gamification.models import ProblemDifficulty
from oioioi.gamification.profile import profile_section, profile_registry
from oioioi.gamification.controllers import CodeSharingController
from oioioi.problems.models import Problem
from oioioi.contests.models import Submission


class TestExperienceModule(TestCase):
    fixtures = ['gamification_users.json',
                'gamification_problem_without_contest.json']

    def setUp(self):
        self._backup_experience_sources = Experience._sources
        Experience.clear_experience_sources()

    def tearDown(self):
        Experience._sources = self._backup_experience_sources

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
        self.assertRaises(ValueError, Experience.exp_to_lvl, -1)
        self.assertRaises(ValueError, Experience.exp_to_lvl, 0)
        self.assertEquals(Experience.exp_to_lvl(1), ExpMultiplier)
        self.assertEquals(Experience.exp_to_lvl(2), ExpBase*ExpMultiplier)
        self.assertEquals(
            Experience.exp_to_lvl(SoftCapLevel + 1),
            Experience.exp_to_lvl(SoftCapLevel) + LinearMultiplier
        )

    def test_experience_from_pair(self):
        test_user = User.objects.get(username='test_user')

        experience = Experience(level=0, experience=ExpMultiplier+2)
        self.assertEquals(experience.level_exp_tuple, (1, 2))
        self.assertEquals(experience.current_level, 1)
        self.assertEquals(experience.current_experience, 2)
        self.assertRaises(ValueError, experience.force_recalculate)

        experience2 = Experience(level=0, experience=ExpMultiplier-1)
        self.assertEquals(experience2.level_exp_tuple, (0, ExpMultiplier-1))

        self.assertRaises(ValueError, Experience,
                          user=test_user,
                          level=1)
        self.assertRaises(ValueError, Experience,
                          user=test_user,
                          experience=1)
        self.assertRaises(ValueError, Experience,
                          user=test_user,
                          level=1,
                          experience=1)

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

    def test_problem_source(self):
        try:
            Experience.add_experience_source(
                PROBLEM_EXPERIENCE_SOURCE
            )

            user = User.objects.get(username='test_user4')

            # test_user has solved a trivial task
            user_exp = Experience(user)
            user_exp.force_recalculate()
            self.assertEquals(user_exp.current_level, 0)
            self.assertEquals(user_exp.current_experience, Lvl1TaskExp)

            # Update on problem difficulty change
            pd = ProblemDifficulty.objects.get(problem__id=10)
            pd.difficulty = DIFFICULTY.EASY
            pd.save()
            self.assertEquals(user_exp.current_level, 1)
            self.assertEquals(user_exp.current_experience, 0)

        finally:
            Experience.clear_experience_sources()


class TestFriends(TestCase):
    fixtures = ['gamification_users.json']

    def areFriends(self, u1, u2):
        friends1 = UserFriends(u1)
        friends2 = UserFriends(u2)

        result_a = friends1.is_friends_with(u2)
        result_b = friends2.is_friends_with(u1)
        self.assertEquals(result_a, result_b)
        self.assertEquals(result_a,
             u1 in friends2.friends.select_related('user').all())
        self.assertEquals(result_a,
             u2 in friends1.friends.select_related('user').all())

        return result_a

    def assertFriends(self, user_a, user_b):
        self.assertTrue(self.areFriends(user_a, user_b))

    def assertNotFriends(self, user_a, user_b):
        self.assertFalse(self.areFriends(user_a, user_b))

    def isRequestSent(self, sender, recipient):
        friends_sender = UserFriends(sender)
        friends_recipient = UserFriends(recipient)

        result_a = friends_sender.sent_request_to(recipient)
        result_b = friends_recipient.has_request_from(sender)
        self.assertEquals(result_a, result_b)
        self.assertEquals(result_a,
             recipient in
             [x.recipient.user for x in friends_sender.my_requests.all()])
        self.assertEquals(result_a,
             sender in
             [x.sender.user for x in friends_recipient.requests_for_me.all()])

        return result_a

    def assertRequestSent(self, sender, recipient):
        self.assertTrue(self.isRequestSent(sender, recipient))

    def assertRequestNotSent(self, sender, recipient):
        self.assertFalse(self.isRequestSent(sender, recipient))

    def get_basic_variables(self):
        test_user1 = User.objects.get(username='test_user')
        test_user2 = User.objects.get(username='test_user2')

        user_friends1 = UserFriends(test_user1)
        user_friends2 = UserFriends(test_user2)

        return test_user1, test_user2, user_friends1, user_friends2

    def test_basic(self):
        u1, u2, _, _ = self.get_basic_variables()
        self.assertNotFriends(u1, u2)
        self.assertRequestNotSent(u1, u2)

    def test_accepting(self):
        u1, u2, friends1, friends2 = self.get_basic_variables()

        friends1.send_friendship_request(u2)
        self.assertNotFriends(u1, u2)
        self.assertRequestSent(u1, u2)

        request = friends1.my_request_for(u2)
        friends2.accept_friendship_request(request)
        self.assertFriends(u1, u2)
        self.assertRequestNotSent(u1, u2)

    def test_refusing(self):
        u1, u2, friends1, friends2 = self.get_basic_variables()

        friends1.send_friendship_request(u2)
        request = friends2.request_from(u1)

        friends2.refuse_friendship_request(request)
        self.assertNotFriends(u1, u2)
        self.assertRequestNotSent(u1, u2)

    def add_friends(self, u1, u2, friends1, friends2):
        friends1.send_friendship_request(u2)
        friends2.send_friendship_request(u1)
        self.assertRequestNotSent(u1, u2)
        self.assertFriends(u1, u2)

    def test_automatic_accepting(self):
        u1, u2, friends1, friends2 = self.get_basic_variables()
        self.add_friends(u1, u2, friends1, friends2)

    def test_removing(self):
        u1, u2, friends1, friends2 = self.get_basic_variables()

        self.add_friends(u1, u2, friends1, friends2)
        friends1.remove_friend(u2)
        self.assertNotFriends(u1, u2)

        self.add_friends(u1, u2, friends1, friends2)
        friends2.remove_friend(u1)
        self.assertNotFriends(u1, u2)

    def test_errors(self):
        u1, u2, friends1, friends2 = self.get_basic_variables()

        # Self-request
        with self.assertRaises(ValueError):
            friends1.send_friendship_request(u1)

        # Duplicated request
        friends1.send_friendship_request(u2)
        with self.assertRaises(ValueError):
            friends1.send_friendship_request(u2)

        # Request to existing friend
        friends2.send_friendship_request(u1)
        with self.assertRaises(ValueError):
            friends1.send_friendship_request(u2)

        friends1.remove_friend(u2)

        # Accepting/refusing invalid request
        friends1.send_friendship_request(u2)
        request = friends1.my_request_for(u2)

        with self.assertRaises(ValueError):
            friends1.accept_friendship_request(request)

        with self.assertRaises(ValueError):
            friends1.refuse_friendship_request(request)

        # Removing non-friend
        with self.assertRaises(ValueError):
            friends1.remove_friend(u2)

        # Getting nonexistent requests
        friends2.refuse_friendship_request(request)
        with self.assertRaises(FriendshipRequest.DoesNotExist):
            friends1.my_request_for(u2)

        with self.assertRaises(FriendshipRequest.DoesNotExist):
            friends1.request_from(u2)

    def test_signals(self):
        sent_log = []
        accepted_log = []
        refused_log = []
        ended_log = []

        # pylint: disable=W0612
        @receiver(FriendshipRequestSent)
        def handle_sent(sender, recipient, **kwargs):
            sent_log.append((sender, recipient))

        @receiver(FriendshipRequestAccepted)
        def handle_accepted(sender, recipient, **kwargs):
            accepted_log.append((sender, recipient))

        @receiver(FriendshipRequestRefused)
        def handle_refused_log(sender, recipient, **kwargs):
            refused_log.append((sender, recipient))

        @receiver(FriendshipEnded)
        def handle_ended_log(sender, recipient, **kwargs):
            ended_log.append((sender, recipient))

        u1, u2, friends1, friends2 = self.get_basic_variables()
        # Send, accept & end friendship usually
        friends1.send_friendship_request(u2)
        friends2.accept_friendship_request(friends2.request_from(u1))
        friends1.remove_friend(u2)

        # Send request, accept friendship by double request, then end
        friends2.send_friendship_request(u1)
        friends1.send_friendship_request(u2)
        friends2.remove_friend(u1)

        # Send & refuse
        friends1.send_friendship_request(u2)
        friends2.refuse_friendship_request(friends2.request_from(u1))

        self.assertEquals(sent_log, [(u1, u2), (u2, u1), (u1, u2)])
        self.assertEquals(accepted_log, [(u2, u1), (u1, u2)])
        self.assertEquals(refused_log, [(u2, u1)])
        self.assertEquals(ended_log, [(u1, u2), (u2, u1)])

    def test_notifications(self):
        u1, u2, friends1, friends2 = self.get_basic_variables()

        notification_log = []

        @classmethod
        def fake_send_notification(cls, user, notification_type,
                    message, arguments):

            if notification_type == 'friends':
                self.assertIn('sender', arguments)

                notification_log.append((arguments['sender'], user,
                        message))

        def checkEntry(sender, recipient, text_fragment, entry):
            self.assertEquals(sender.username, entry[0])
            self.assertEquals(recipient, entry[1])
            self.assertIn(text_fragment, entry[2])

        send_notification_backup = NotificationHandler.send_notification
        NotificationHandler.send_notification = fake_send_notification

        try:
            friends1.send_friendship_request(u2)
            friends2.accept_friendship_request(friends2.request_from(u1))
            friends1.remove_friend(u2)

            friends2.send_friendship_request(u1)
            friends1.refuse_friendship_request(friends1.request_from(u2))

            self.assertEquals(len(notification_log), 5)
            checkEntry(u1, u2, 'sent', notification_log[0])
            checkEntry(u2, u1, 'accepted', notification_log[1])
            checkEntry(u1, u2, 'no longer wants', notification_log[2])
            checkEntry(u2, u1, 'sent', notification_log[3])
            checkEntry(u1, u2, 'refused', notification_log[4])

        finally:
            NotificationHandler.send_notification = send_notification_backup


class TestProfileView(TestCase):
    fixtures = ['test_users.json']

    def test_experience_counter(self):
        url = reverse('view_current_profile')
        url_other = reverse('view_profile', args=['test_user2'])

        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertIn('0</text>', response.content)
        self.assertIn('Level: 0', response.content)
        self.assertIn('0%', response.content)

        response = self.client.get(url_other)
        self.assertIn('0</text>', response.content)
        self.assertIn('Level: 0', response.content)
        self.assertIn('0%', response.content)

        exp_to_lvl = Experience.exp_to_lvl

        class TrivialSource(ExperienceSource):
            def get_experience(self, user):
                if user.username == 'test_user':
                    return exp_to_lvl(1) + 10
                else:
                    return exp_to_lvl(1) + exp_to_lvl(2) + 10

            def force_recalculate(self, user):
                pass

        try:
            Experience.add_experience_source(TrivialSource())
            response = self.client.get(url)
            self.assertIn('1</text>', response.content)
            self.assertIn('Level: 1', response.content)
            self.assertIn('Experience: %d%%' % (100 * 10 / exp_to_lvl(2)),
                          response.content)

            response = self.client.get(url_other)
            self.assertIn('2</text>', response.content)
            self.assertIn('Level: 2', response.content)
            self.assertIn('Experience: %d%%' % (100 * 10 / exp_to_lvl(3)),
                          response.content)
        finally:
            Experience.clear_experience_sources()

    def test_friendship_actions(self):
        test_user1 = User.objects.get(username='test_user')
        test_user2 = User.objects.get(username='test_user2')

        friends = UserFriends(test_user1)

        # Sending request
        self.client.login(username='test_user')
        self.client.post(reverse('send_friendship_request',
                args=['test_user2']))
        self.assertTrue(friends.sent_request_to(test_user2))

        # Accepting request
        self.client.login(username='test_user2')
        self.client.post(reverse('accept_friendship_request',
                args=['test_user']))
        self.assertTrue(friends.is_friends_with(test_user2))

        # Ending friendship
        self.client.post(reverse('remove_friend',
                args=['test_user']))
        self.assertFalse(friends.is_friends_with(test_user2))

        # Refusing request
        self.client.post(reverse('send_friendship_request',
                args=['test_user']))
        self.client.login(username='test_user')
        self.client.post(reverse('refuse_friendship_request',
                args=['test_user2']))
        self.assertFalse(friends.has_request_from(test_user2))

    def test_invite_list(self):
        test_user1 = User.objects.get(username='test_user')
        test_user2 = User.objects.get(username='test_user2')

        url = reverse('view_current_profile')

        # Check visibility without an invite
        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertNotIn('Pending invites', response.content)
        self.assertNotIn('test_user2', response.content)

        # Check visibility with an invite
        UserFriends(test_user2).send_friendship_request(test_user1)
        response = self.client.get(url)
        self.assertIn('Pending invites', response.content)
        self.assertIn('test_user2', response.content)

    def test_friends_list(self):
        test_user1 = User.objects.get(username='test_user')
        test_user2 = User.objects.get(username='test_user2')

        url = reverse('view_current_profile')
        user_text = 'test_user2</h2></a>'

        # Check user profile
        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertNotIn(user_text, response.content)

        UserFriends(test_user1).send_friendship_request(test_user2)
        UserFriends(test_user2).send_friendship_request(test_user1)

        response = self.client.get(url)
        self.assertIn(user_text, response.content)

        # Check visibility from outside
        self.client.login(username='test_user2')
        response = self.client.get(reverse('view_profile', args=['test_user']))
        self.assertNotIn(user_text, response.content)


class TestProfileTabs(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        # pylint: disable=global-statement
        global profile_registry
        self.profile_backup = profile_registry
        profile_registry = OrderedRegistry()

    def tearDown(self):
        # pylint: disable=global-statement
        global profile_registry
        profile_registry = self.profile_backup

    def test_tabs(self):
        tab_content = '<b>Hello, world!</b>'

        @profile_section(0)
        def dummy_section(request, shown_user):
            return tab_content

        url = reverse('view_current_profile')
        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertIn(tab_content, response.content)


class TestCodeSharingFriends(TestCase):
    fixtures = ['gamification_users.json', 'test_friendships.json',
                'test_allowsharingprefs.json', 'gamification_problems.json',
                'gamification_submissions.json',
                'test_submission_source.json',
                'gamification_problem_without_contest.json']

    def ensure_enabled(self):
        self.assertTrue(
            CODE_SHARING_FRIENDS_ENABLED,
            'Can\'t check friend\'s code sharing if they aren\'t enabled'
        )

    def setUp(self):
        self.ensure_enabled()
        # pylint: disable=global-statement
        global CODE_SHARING_PREFERENCES_DEFAULT
        self._old_sharing = CODE_SHARING_PREFERENCES_DEFAULT
        CODE_SHARING_PREFERENCES_DEFAULT = False

    def tearDown(self):
        # pylint: disable=global-statement
        global CODE_SHARING_PREFERENCES_DEFAULT
        CODE_SHARING_PREFERENCES_DEFAULT = self._old_sharing

    def test_cansee(self):
        controller = CodeSharingController()
        user1 = User.objects.get(pk=1001)
        user2 = User.objects.get(pk=1002)
        user3 = User.objects.get(pk=1003)
        user4 = User.objects.get(pk=1004)
        problem = Problem.objects.get(pk=1)
        # user2 doesn't allow code sharing (no row in model, defaults to false)
        self.assertFalse(controller.can_see_code(problem, user1, user2))
        # user1 doesn't allow code sharing (disabled option in preferences)
        self.assertFalse(controller.can_see_code(problem, user2, user1))
        # user1 and user3 are not friends
        self.assertFalse(controller.can_see_code(problem, user1, user3))
        # user3 doesn't have submissions
        self.assertFalse(controller.can_see_code(problem, user2, user3))
        # user2 doesn't allow code sharing (no row in model, defaults to false)
        self.assertFalse(controller.can_see_code(problem, user3, user2))
        #
        # [!!!] Everything in order
        #
        self.assertTrue(controller.can_see_code(problem, user3, user4))
        self.assertTrue(controller.can_see_code(problem, user2, user4))
        # No submission
        self.assertFalse(controller.can_see_code(problem, user4, user3))
        # Not friends
        self.assertFalse(controller.can_see_code(problem, user1, user4))
        # Not allowed
        self.assertFalse(controller.can_see_code(problem, user4, user2))

    def test_sharedwithme(self):
        controller = CodeSharingController()
        problem = Problem.objects.get(pk=1)
        user1 = User.objects.get(pk=1001)
        user2 = User.objects.get(pk=1002)
        user4 = User.objects.get(pk=1004)
        user4_submission = Submission.objects.get(pk=1)
        self.assertEquals(
            list(controller.shared_with_me(problem, user1).all()),
            [])
        self.assertEquals(
            list(controller.shared_with_me(problem, user2).all()),
            [user4_submission])
        self.assertEquals(
            list(controller.shared_with_me(problem, user4).all()),
            [])

    def test_is_shared_visible(self):
        def check_submission(submission_id, view_name):
            submission = Submission.objects.get(pk=submission_id)

            kwargs = {'submission_id': submission.id}
            if submission.problem_instance.contest is not None:
                kwargs['contest_id'] = submission.problem_instance.contest.id
            url = reverse(view_name, kwargs=kwargs)

            # 2 & 4 are friends, 1 & 4 are not
            self.client.login(username='test_user')
            response = self.client.get(url)
            self.assertEquals(response.status_code, 403)

            self.client.login(username='test_user2')
            response = self.client.get(url)
            self.assertEquals(response.status_code, 200)

        check_submission(1, 'show_submission_source')
        check_submission(2, 'show_submission_source_without_contest')


class DifficultyTest(TestCase):
    fixtures = ['gamification_problems.json',
                'gamification_sinol_config.json']

    def setUp(self):
        parse_old_problems()

    def test_get_difficulty(self):
        problem1 = Problem.objects.get(pk=1)
        problem2 = Problem.objects.get(pk=2)
        problem3 = Problem.objects.get(pk=3)
        problem4 = Problem.objects.get(pk=4)

        # Twice to check lazy initiation
        self.assertEquals(get_problem_difficulty(problem1), DIFFICULTY.TRIVIAL)
        self.assertEquals(get_problem_difficulty(problem1), DIFFICULTY.TRIVIAL)
        self.assertEquals(get_problem_difficulty(problem2), DIFFICULTY.MEDIUM)
        self.assertEquals(get_problem_difficulty(problem3), None)
        self.assertEquals(get_problem_difficulty(problem4), None)

    def test_problems_by_difficulty(self):
        # Trivial
        problem1 = Problem.objects.get(pk=1)
        # Medium
        problem2 = Problem.objects.get(pk=2)
        problem5 = Problem.objects.get(pk=5)

        trivial_result =\
            list(get_problems_by_difficulty(DIFFICULTY.TRIVIAL).all())
        self.assertEqual(trivial_result, [problem1])
        medium_result =\
            list(get_problems_by_difficulty(DIFFICULTY.MEDIUM).all())
        self.assertIn(problem2, medium_result)
        self.assertIn(problem5, medium_result)
        self.assertEqual(len(medium_result), 2)

        hard_result = list(get_problems_by_difficulty(DIFFICULTY.HARD).all())
        self.assertEqual(hard_result, [])
