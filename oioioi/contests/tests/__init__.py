from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from oioioi.contests.controllers import ContestController, \
        RegistrationController, PastRoundsHiddenContestControllerMixin

class PrivateRegistrationController(RegistrationController):
    def anonymous_can_enter_contest(self):
        return False

    def filter_participants(self, queryset):
        return queryset.none()


class PrivateContestController(ContestController):
    def registration_controller(self):
        return PrivateRegistrationController(self.contest)

    def update_submission_score(self, submission):
        raise NotImplementedError

    def render_submission(self, request, submission):
        raise NotImplementedError

    def create_submission(self, request, problem_instance, form_data,
                          **kwargs):
        raise NotImplementedError


class PastRoundsHiddenContestController(ContestController):
    pass
PastRoundsHiddenContestController.mix_in(
    PastRoundsHiddenContestControllerMixin
)


class SubmitFileMixin(object):
    def submit_file(self, contest, problem_instance, file_size=1024,
            file_name='submission.cpp', kind='NORMAL', user=None):
        url = reverse('submit', kwargs={'contest_id': contest.id})
        file = ContentFile('a' * file_size, name=file_name)
        post_data = {
            'problem_instance_id': problem_instance.id,
            'file': file,
        }
        if user:
            post_data.update({
                'kind': kind,
                'user': user,
            })
        return self.client.post(url, post_data)

    def submit_code(self, contest, problem_instance, code='', prog_lang='C',
            send_file=False, kind='NORMAL', user=None):
        url = reverse('submit', kwargs={'contest_id': contest.id})
        file = None
        if send_file:
            file = ContentFile('a' * 1024, name='a.c')
        post_data = {
                'problem_instance_id': problem_instance.id,
                'file': file,
                'code': code,
                'prog_lang': prog_lang,
        }
        if user:
            post_data.update({
                'kind': kind,
                'user': user,
            })
        return self.client.post(url, post_data)

    def _assertSubmitted(self, contest, response):
        self.assertEqual(302, response.status_code)
        submissions = reverse('my_submissions',
                              kwargs={'contest_id': contest.id})
        self.assertTrue(response["Location"].endswith(submissions))

    def _assertNotSubmitted(self, contest, response):
        self.assertEqual(302, response.status_code)
        submissions = reverse('my_submissions',
                              kwargs={'contest_id': contest.id})
        self.assertFalse(response["Location"].endswith(submissions))
