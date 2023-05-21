from django.core.files.base import ContentFile
from django.db.models import Q
from django.urls import reverse

from oioioi.base.utils.query_helpers import Q_always_false
from oioioi.contests.controllers import (
    ContestController,
    PastRoundsHiddenContestControllerMixin,
    RegistrationController,
)


class PrivateRegistrationController(RegistrationController):
    @classmethod
    def anonymous_can_enter_contest(cls):
        return False

    def user_contests_query(self, request):
        return Q_always_false()

    def filter_participants(self, queryset):
        return queryset.none()


class PrivateContestController(ContestController):
    def registration_controller(self):
        return PrivateRegistrationController(self.contest)

    def update_submission_score(self, submission):
        raise NotImplementedError

    def render_submission(self, request, submission):
        raise NotImplementedError

    def create_submission(self, request, problem_instance, form_data, **kwargs):
        raise NotImplementedError


class PastRoundsHiddenContestController(ContestController):
    pass


PastRoundsHiddenContestController.mix_in(PastRoundsHiddenContestControllerMixin)


class SubmitMixin(object):
    def _assertSubmitted(self, contest, response):
        self.assertEqual(302, response.status_code)
        submissions = reverse('my_submissions', kwargs={'contest_id': contest.id})
        self.assertTrue(response["Location"].endswith(submissions))

    def _assertNotSubmitted(self, contest, response):
        self.assertEqual(302, response.status_code)
        submissions = reverse('my_submissions', kwargs={'contest_id': contest.id})
        self.assertFalse(response["Location"].endswith(submissions))


def make_empty_contest_formset():
    formsets = (
        ('round_set', 0, 0, 0, 1000),
        ('c_attachments', 0, 0, 0, 1000),
        ('usergroupranking_set', 0, 0, 0, 1000),
        ('contestlink_set', 0, 0, 0, 1000),
        ('messagenotifierconfig_set', 0, 0, 0, 1000),
        ('mail_submission_config', 1, 0, 0, 1),
        ('prizegiving_set', 0, 0, 0, 1000),
        ('prize_set', 0, 0, 0, 1000),
        ('teamsconfig', 1, 0, 0, 1),
        ('problemstatementconfig', 1, 0, 0, 1),
        ('rankingvisibilityconfig', 0, 0, 0, 1),
        ('registrationavailabilityconfig', 0, 0, 0, 1),
        ('balloonsdeliveryaccessdata', 1, 0, 0, 1),
        ('statistics_config', 1, 0, 0, 1),
        ('exclusivenessconfig_set', 0, 0, 0, 1000),
        ('complaints_config', 1, 0, 0, 1),
        ('disqualifications_config', 1, 0, 0, 1),
        ('contesticon_set', 0, 0, 0, 1000),
        ('contestlogo', 1, 0, 0, 1),
        ('programs_config', 1, 0, 0, 1),
        ('contestcompiler_set', 0, 0, 0, 1000),
    )
    data = dict()
    for (name, total, initial, min_num, max_num) in formsets:
        data['{}-TOTAL_FORMS'.format(name)] = total
        data['{}-INITIAL_FORMS'.format(name)] = initial
        data['{}-MIN_NUM_FORMS'.format(name)] = min_num
        data['{}-MAX_NUM_FORMS'.format(name)] = max_num
    return data
