import os
import re
from datetime import UTC, datetime, timedelta  # pylint: disable=E0611

import pytest
from django.contrib.admin.utils import quote
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase, fake_time, fake_timezone_now
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.handlers import update_user_results
from oioioi.contests.models import Contest, ProblemInstance, Round
from oioioi.evalmgr.tasks import create_environ
from oioioi.oi.management.commands import import_schools
from oioioi.oi.models import OIDataConfirmationSettings, OIRegistration, School
from oioioi.participants.models import Participant, TermsAcceptedPhrase
from oioioi.programs.tests import SubmitFileMixin


class TestOIAdmin(TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_oi_registration",
        "test_permissions",
        "test_school_types",
    ]

    def test_admin_menu(self):
        contest = Contest.objects.get()
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()

        self.assertTrue(self.client.login(username="test_admin"))
        url = reverse("default_contest_view", kwargs={"contest_id": contest.id})
        response = self.client.get(url, follow=True)
        self.assertContains(response, "Schools")
        self.assertNotContains(response, "Regions")

    def test_schools_import(self):
        filename = os.path.join(os.path.dirname(__file__), "files", "rspo_schools.csv")
        backup_filename = os.path.join(os.path.dirname(__file__), "files", "rspo_schools.bak")
        manager = import_schools.Command()
        manager.run_from_argv(["manage.py", "import_schools", "--first-import", filename, "--backup-filename", backup_filename])
        self.assertEqual(School.objects.count(), 26)
        school = School.objects.get(postal_code="02-172")
        self.assertEqual(school.city, "Włochy")

    def test_safe_exec_mode(self):
        contest = Contest.objects.get()
        self.assertEqual(contest.controller.get_safe_exec_mode(), "sio2jail")

    def test_terms_accepted_phrase_inline_admin_permissions(self):
        OIRegistration.objects.all().delete()

        contest = Contest.objects.get()
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()

        # Logging as superuser.
        self.assertTrue(self.client.login(username="test_admin"))
        self.client.get("/c/c/")  # 'c' becomes the current contest
        url = reverse("oioioiadmin:contests_contest_change", args=(quote("c"),))

        response = self.client.get(url)
        self.assertContains(response, "Text asking participant to accept contest terms")

        # Checks if the field is editable.
        self.assertContains(response, "id_terms_accepted_phrase-0-text")

        # Logging as contest admin.
        self.assertTrue(self.client.login(username="test_contest_admin"))
        self.client.get("/c/c/")  # 'c' becomes the current contest
        url = reverse("oioioiadmin:contests_contest_change", args=(quote("c"),))

        response = self.client.get(url)
        self.assertContains(response, "Text asking participant to accept contest terms")

        # Checks if the field is editable.
        self.assertContains(response, "id_terms_accepted_phrase-0-text")

    def test_terms_accepted_phrase_inline_edit_restrictions(self):
        contest = Contest.objects.get()
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()

        self.assertTrue(self.client.login(username="test_admin"))
        self.client.get("/c/c/")  # 'c' becomes the current contest
        url = reverse("oioioiadmin:contests_contest_change", args=(quote("c"),))

        response = self.client.get(url)
        self.assertContains(response, "Text asking participant to accept contest terms")

        # Checks if the field is not editable.
        self.assertNotContains(response, "id_terms_accepted_phrase-0-text")


class TestOIRegistration(TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_schools",
        "test_terms_accepted_phrase",
    ]

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()

    def test_participants_accounts_menu(self):
        contest = Contest.objects.get()

        url = reverse("default_contest_view", kwargs={"contest_id": contest.id})

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(url, follow=True)
        self.assertContains(response, "Register to the contest")
        self.assertNotContains(response, "Edit contest registration")

        user = User.objects.get(username="test_user")
        p = Participant(contest=contest, user=user)
        p.save()

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(url, follow=True)
        self.assertNotContains(response, "Register to the contest")
        self.assertContains(response, "Edit contest registration")

    def test_participants_unregister_forbidden(self):
        contest = Contest.objects.get()

        url = reverse("participants_unregister", kwargs={"contest_id": contest.id})

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.post(url, {"post": "yes"})
        self.assertEqual(403, response.status_code)

        user = User.objects.get(username="test_user")
        p = Participant(contest=contest, user=user, status="BANNED")
        p.save()
        self.assertEqual(Participant.objects.count(), 1)

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.post(url, {"post": "yes"})
        self.assertEqual(403, response.status_code)

        p.status = "ACTIVE"
        p.save()

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.post(url, {"post": "yes"})
        self.assertEqual(403, response.status_code)
        self.assertEqual(Participant.objects.count(), 1)

    def test_default_terms_accepted_phrase(self):
        TermsAcceptedPhrase.objects.get().delete()
        contest = Contest.objects.get()
        url = reverse("participants_register", kwargs={"contest_id": contest.id})

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(url)

        self.assertContains(response, "terms accepted")

    def test_participants_registration(self):
        contest = Contest.objects.get()
        user = User.objects.get(username="test_user")
        url = reverse("participants_register", kwargs={"contest_id": contest.id})
        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(url)

        self.assertContains(response, "Postal code")
        self.assertContains(response, "School")
        self.assertContains(response, "Test terms accepted")
        self.assertContains(response, "1977")

        user.first_name = "Sir Lancelot"
        user.last_name = "du Lac"
        user.save()
        reg_data = {
            "address": "The Castle",
            "postal_code": "31-337",
            "city": "Camelot",
            "phone": "000-000-000",
            "birthday_month": "5",
            "birthday_day": "25",
            "birthday_year": "1975",
            "birthplace": "Lac",
            "t_shirt_size": "L",
            "school": "1",
            "class_type": "1LO",
            "terms_accepted": "t",
        }

        response = self.client.post(url, reg_data)
        self.assertEqual(302, response.status_code)

        registration = OIRegistration.objects.get(participant__user=user)
        self.assertEqual(registration.address, reg_data["address"])
        self.assertEqual(registration.school.address, "Nowowiejska 37a")

    @pytest.mark.xfail
    def test_registration_with_new_school(self):
        """currently the registration form for OI does not support adding new school"""
        contest = Contest.objects.get()
        user = User.objects.get(username="test_user")
        url = reverse("participants_register", kwargs={"contest_id": contest.id})
        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(url)
        self.assertContains(response, "Postal code")
        self.assertContains(response, "School")

        user.first_name = "Sir Lancelot"
        user.last_name = "du Lac"
        user.save()
        reg_data = {
            "address": "The Castle",
            "postal_code": "31-337",
            "school": "999",
            "terms_accepted": "t",
            "_add_school": "add it",
        }

        response = self.client.post(url, reg_data, follow=True)
        add_school_url = reverse("add_school")
        self.assertRedirects(response, add_school_url)
        self.assertIn("oi_oiregistrationformdata", self.client.session)

        school_data = {
            "name": "Lady of the Lake",
            "address": "some lake",
            "postal_code": "13-337",
            "city": "N/A",
            "province": "mazowieckie",
            "phone": "000-000-000",
            "email": "not.applicable@example.com",
        }

        response = self.client.post(add_school_url, school_data, follow=True)
        self.assertRedirects(response, url)
        school = School.objects.get(pk=5)
        self.assertEqual(school.name, school_data["name"])
        self.assertTrue(school.is_active)
        self.assertFalse(school.is_approved)

        self.assertContains(response, "Postal code")
        self.assertContains(response, reg_data["address"])
        self.assertContains(response, "Lady of the Lake")


class TestOIViews(TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_submission",
    ]

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_contest_visibility(self):
        contest = Contest(id="visible", name="Visible Contest")
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()

        response = self.client.get(reverse("select_contest"))
        self.assertEqual(len(response.context["contests"]), 2)
        self.assertContains(response, "Visible Contest")

        response = self.client.get(reverse("select_contest"))
        self.assertEqual(len(response.context["contests"]), 2)
        self.assertContains(response, "Visible Contest")

    def test_contest_access(self):
        contest = Contest.objects.get()
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()

        user = User.objects.get(username="test_user")
        p = Participant(contest=contest, user=user, status="BANNED")
        p.save()

        url = reverse("default_contest_view", kwargs={"contest_id": contest.id})

        self.assertTrue(self.client.login(username="test_user2"))
        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)

        p.status = "ACTIVE"
        p.save()

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)

    def test_ranking_access(self):
        contest = Contest.objects.get()
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()
        round = contest.round_set.get()
        user = User.objects.get(username="test_user")
        p = Participant(contest=contest, user=user)
        p.save()
        url = reverse("default_ranking", kwargs={"contest_id": contest.id})

        with fake_timezone_now(round.results_date + timedelta(days=1)):
            self.assertTrue(self.client.login(username="test_user"))
            response = self.client.get(url)
            self.assertContains(response, "No rankings available.")
            self.assertTrue(self.client.login(username="test_admin"))
            response = self.client.get(url)

            user_pattern = r">\s*Test User\s*</a>"
            self.assertTrue(re.search(user_pattern, response.content.decode("utf-8")))


class TestSchoolAdding(TestCase):
    fixtures = ["test_users", "test_contest", "test_schools"]

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()

    def test_schools_similar_view(self):
        self.assertTrue(self.client.login(username="test_user"))

        self.client.get("/c/c/")  # 'c' becomes the current contest
        url = reverse("schools_similar")

        response = self.client.post(url, {"city": "Warszawa"})
        self.assertContains(response, "LO")
        self.assertContains(response, "Gimnazjum")
        self.assertContains(response, "click its name")


class TestSchoolAdmin(TestCase):
    fixtures = ["test_users", "test_contest", "test_schools"]

    def test_schools_similar_finding(self):
        s = School.objects.all()
        self.assertTrue(s[0].is_similar(s[1]))
        self.assertTrue(s[2].is_similar(s[3]))
        self.assertTrue(s[3].is_similar(s[2]))
        self.assertFalse(s[1].is_similar(s[2]))


class TestSchoolMerging(TestCase):
    fixtures = ["test_users", "test_contest", "test_schools"]

    def _call_admin_merge_action(self, schools_pk_list):
        url = reverse("oioioiadmin:oi_school_changelist")
        data = {"_selected_action": schools_pk_list, "action": "merge_action"}
        return self.client.post(url, data, follow=True)

    def test_schools_merging_unsuccessfull(self):
        contest = Contest.objects.get()
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()

        user = User.objects.get(username="test_user")
        url = reverse("participants_register", kwargs={"contest_id": contest.id})
        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(url)

        user.first_name = "Sir Lancelot"
        user.last_name = "du Lac"
        user.save()
        reg_data = {
            "address": "The Castle",
            "postal_code": "31-337",
            "city": "Camelot",
            "phone": "000-000-000",
            "birthday_month": "5",
            "birthday_day": "25",
            "birthday_year": "1975",
            "birthplace": "Lac",
            "t_shirt_size": "L",
            "school": "2",
            "class_type": "1LO",
            "terms_accepted": "t",
        }

        response = self.client.post(url, reg_data)
        self.assertEqual(302, response.status_code)

        s1 = School.objects.get(pk=1)
        s2 = School.objects.get(pk=2)
        s2.is_approved = False
        s2.save()

        self.assertTrue(self.client.login(username="test_admin"))

        response = self._call_admin_merge_action(1)
        self.assertContains(response, "exactly one")

        response = self._call_admin_merge_action(2)
        self.assertContains(response, "exactly one")

        response = self._call_admin_merge_action((1, 3))
        self.assertContains(response, "exactly one")

        response = self._call_admin_merge_action((1, 2, 3))
        self.assertContains(response, "exactly one")

        s2reg = OIRegistration.objects.get(participant__user=user)
        self.assertFalse(s2reg.school == s1)
        self.assertTrue(s2reg.school == s2)
        response = self._call_admin_merge_action((1, 2))
        self.assertNotContains(response, "exactly one")
        s2reg = OIRegistration.objects.get(participant__user=user)
        self.assertTrue(s2reg.school == s1)
        self.assertFalse(s2reg.school == s2)
        self.assertTrue(s2 not in School.objects.all())


class TestOISubmit(TestCase, SubmitFileMixin):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
    ]

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()

    def test_submit_permissions(self):
        contest = Contest.objects.get()

        round = Round.objects.get(pk=1)
        problem_instance = ProblemInstance.objects.get(pk=1)
        self.assertTrue(problem_instance.round == round)
        round.start_date = datetime(2012, 7, 31, tzinfo=UTC)
        round.end_date = datetime(2012, 8, 5, tzinfo=UTC)
        round.save()

        user = User.objects.get(username="test_user")
        p = Participant(contest=contest, user=user, status="BANNED")
        p.save()

        with fake_time(datetime(2012, 8, 4, 0, 5, tzinfo=UTC)):
            self.client.logout()
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertContains(response, "Sorry, there are no problems")

            self.assertTrue(self.client.login(username="test_user2"))
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertContains(response, "Sorry, there are no problems")

            self.assertTrue(self.client.login(username="test_user"))
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertContains(response, "Sorry, there are no problems")

            p.status = "ACTIVE"
            p.save()

            self.assertTrue(self.client.login(username="test_user"))
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)


class TestOIOnsiteSubmit(TestCase, SubmitFileMixin):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
    ]

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = "oioioi.oi.controllers.OIOnsiteContestController"
        contest.save()

    def test_submit_permissions(self):
        contest = Contest.objects.get()

        round = Round.objects.get(pk=1)
        problem_instance = ProblemInstance.objects.get(pk=1)
        self.assertTrue(problem_instance.round == round)
        round.start_date = datetime(2012, 7, 31, tzinfo=UTC)
        round.end_date = datetime(2012, 8, 5, tzinfo=UTC)
        round.save()

        user = User.objects.get(username="test_user")
        p = Participant(contest=contest, user=user, status="BANNED")
        p.save()

        with fake_time(datetime(2012, 8, 4, 0, 5, tzinfo=UTC)):
            self.client.logout()
            response = self.submit_file(contest, problem_instance)
            self._assertNotSubmitted(contest, response)

            self.assertTrue(self.client.login(username="test_user2"))
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(403, response.status_code)

            self.assertTrue(self.client.login(username="test_user"))
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(403, response.status_code)

            p.status = "ACTIVE"
            p.save()

            self.assertTrue(self.client.login(username="test_user"))
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)


class TestIgnoringCE(TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_submission",
        "test_submissions_CE",
    ]

    def _test(self, controller_name):
        contest = Contest.objects.get()
        contest.controller.name = controller_name
        contest.save()

        test_env = create_environ()
        test_env["problem_instance_id"] = 1
        test_env["round_id"] = 1
        test_env["contest_id"] = contest.id

        url = reverse("default_ranking", kwargs={"contest_id": contest.id})

        for i in [1, 3, 4]:
            test_env["submission_id"] = i
            update_user_results(test_env)

        self.assertTrue(self.client.login(username="test_admin"))
        response = self.client.get(url)
        self.assertContains(response, "Test User")
        self.assertNotContains(response, "Test User 2")
        self.assertContains(response, "34")

    def test_all_oi_style_contests(self):
        self._test("oioioi.oi.controllers.OIContestController")
        self._test("oioioi.oi.controllers.OIOnsiteContestController")


class TestUserInfo(TestCase):
    fixtures = ["test_users", "test_contest", "test_schools", "test_permissions"]

    def test_user_info_page(self):
        contest = Contest.objects.get()
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()

        user = User.objects.get(username="test_user")
        url = reverse("participants_register", kwargs={"contest_id": contest.id})
        self.assertTrue(self.client.login(username="test_user"))
        self.client.get(url)

        user.first_name = "Sir Lancelot"
        user.last_name = "du Lac"
        user.save()
        reg_data = {
            "address": "The Castle",
            "postal_code": "31-337",
            "city": "Camelot",
            "phone": "000-000-000",
            "birthday_month": "5",
            "birthday_day": "25",
            "birthday_year": "1975",
            "birthplace": "Lac",
            "t_shirt_size": "L",
            "school": "1",
            "class_type": "1LO",
            "terms_accepted": "t",
        }

        response = self.client.post(url, reg_data)
        self.assertEqual(302, response.status_code)
        url = reverse("user_info", kwargs={"contest_id": contest.id, "user_id": user.id})

        reg_data["birthday_day"] = "May 25, 1975"
        to_delete = ["school", "birthday_month", "birthday_year", "terms_accepted"]
        for k in to_delete:
            del reg_data[k]

        for k in reg_data:
            reg_data[k] = ": " + reg_data[k]

        can_see_list = [
            ("test_admin", True),
            ("test_observer", False),
            ("test_personal_data_user", True),
        ]

        for username, can_see in can_see_list:
            self.assertTrue(self.client.login(username=username))
            response = self.client.get(url)
            self.client.logout()

            for k in reg_data:
                if can_see:
                    self.assertContains(response, reg_data[k])
                else:
                    self.assertNotContains(response, reg_data[k], status_code=403)


class TestOIDataConfirmation(TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_oi_registration",
        "test_permissions",
        "test_school_types",
    ]

    def setUp(self):
        self.contest = Contest.objects.get()
        self.contest.controller_name = "oioioi.oi.controllers.OIFinalOnsiteContestController"
        self.contest.save()

        now = datetime.now(UTC)
        round = Round.objects.get(pk=1)
        round.is_trial = True
        round.start_date = now - timedelta(days=1)
        round.end_date = now + timedelta(days=1)
        round.save()

        self.confirm_url = reverse("oi_confirm_data", kwargs={"contest_id": self.contest.id})
        self.contest_url = reverse("default_contest_view", kwargs={"contest_id": self.contest.id})

    def test_unconfirmed_participant_is_redirected_to_confirmation(self):
        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(self.contest_url)
        self.assertRedirects(response, self.confirm_url, fetch_redirect_response=False)

    def test_confirmation_updates_data_and_stops_redirects(self):
        self.assertTrue(self.client.login(username="test_user"))
        post_data = {
            # first_name, last_name and email are read-only here; changing
            # them requires the account edit-profile page.
            "first_name": "Lancelot",
            "last_name": "du Lac",
            "email": "lancelot@example.com",
            "address": "The Castle",
            "postal_code": "31-337",
            "city": "Camelot",
            "phone": "000-000-000",
            "birthday_day": "25",
            "birthday_month": "5",
            "birthday_year": "1975",
            "birthplace": "Lac",
            "t_shirt_size": "L",
            "school": "1",
            "class_type": "1LO",
        }
        response = self.client.post(self.confirm_url, post_data)
        self.assertRedirects(response, self.contest_url, fetch_redirect_response=False)
        # No longer redirected once the data is confirmed.
        response = self.client.get(self.contest_url)
        self.assertNotIn("confirm-data", response.get("Location", ""))

        reg = OIRegistration.objects.get(participant__user__username="test_user")
        self.assertIsNotNone(reg.data_confirmed_at)
        user = User.objects.get(username="test_user")
        # Posted first_name/last_name/email are ignored: these fields are
        # disabled and can only be changed via edit_profile.
        self.assertEqual((user.first_name, user.last_name, user.email), ("Test", "User", "test_user@example.com"))

    def test_no_redirect_outside_active_trial_round(self):
        Round.objects.filter(pk=1).update(is_trial=False)
        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(self.contest_url)
        self.assertNotIn("confirm-data", response.get("Location", ""))

    def test_participant_without_oiregistration_is_redirected_and_creates_one(self):
        # Onsite finalists register via OnsiteRegistration and usually have no
        # OIRegistration in the finals contest, yet must still confirm.
        user = User.objects.get(username="test_user2")
        Participant.objects.create(contest=self.contest, user=user, status="ACTIVE")
        self.assertFalse(OIRegistration.objects.filter(participant__user=user).exists())

        self.assertTrue(self.client.login(username="test_user2"))
        response = self.client.get(self.contest_url)
        self.assertRedirects(response, self.confirm_url, fetch_redirect_response=False)

        post_data = {
            "first_name": "Percival",
            "last_name": "de Galles",
            "email": "percival@example.com",
            "address": "Round Table",
            "postal_code": "31-337",
            "city": "Camelot",
            "phone": "000-000-000",
            "birthday_day": "1",
            "birthday_month": "1",
            "birthday_year": "1980",
            "birthplace": "Galles",
            "t_shirt_size": "M",
            "school": "1",
            "class_type": "2LO",
        }
        response = self.client.post(self.confirm_url, post_data)
        self.assertRedirects(response, self.contest_url, fetch_redirect_response=False)

        reg = OIRegistration.objects.get(participant__user=user)
        self.assertIsNotNone(reg.data_confirmed_at)
        self.assertEqual(reg.city, "Camelot")
        user.refresh_from_db()
        # Posted first_name/last_name/email are ignored: these fields are
        # disabled and can only be changed via edit_profile.
        self.assertEqual(
            (user.first_name, user.last_name, user.email),
            ("Test", "User 2", "test_user2@example.com"),
        )

        # Confirmed once, no more redirects.
        response = self.client.get(self.contest_url)
        self.assertNotIn("confirm-data", response.get("Location", ""))

    def test_no_redirect_when_confirmation_disabled_in_settings(self):
        OIDataConfirmationSettings.objects.create(contest=self.contest, is_enabled=False)
        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(self.contest_url)
        self.assertNotIn("confirm-data", response.get("Location", ""))

    def test_prefill_uses_configured_source_contest(self):
        user = User.objects.get(username="test_user2")

        other_contest = Contest.objects.create(id="other", name="Other contest", controller_name="oioioi.oi.controllers.OIContestController")
        other_participant = Participant.objects.create(contest=other_contest, user=user, status="ACTIVE")
        OIRegistration.objects.create(
            participant=other_participant,
            address="Wrong Address",
            postal_code="00-000",
            city="Wrongtown",
            birthday="1970-01-01",
            birthplace="Nowhere",
            t_shirt_size="S",
            school_id=1,
            class_type="1LO",
        )

        newer_contest = Contest.objects.create(id="newer", name="Newer contest", controller_name="oioioi.oi.controllers.OIContestController")
        newer_participant = Participant.objects.create(contest=newer_contest, user=user, status="ACTIVE")
        OIRegistration.objects.create(
            participant=newer_participant,
            address="Newest Address",
            postal_code="11-111",
            city="Newtown",
            birthday="1970-01-01",
            birthplace="Nowhere",
            t_shirt_size="S",
            school_id=1,
            class_type="1LO",
        )

        OIDataConfirmationSettings.objects.create(contest=self.contest, is_enabled=True, source_contest=other_contest)

        Participant.objects.create(contest=self.contest, user=user, status="ACTIVE")

        self.assertTrue(self.client.login(username="test_user2"))
        response = self.client.get(self.confirm_url)
        self.assertContains(response, "Wrong Address")
        self.assertNotContains(response, "Newest Address")
