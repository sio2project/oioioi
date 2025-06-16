from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.query_helpers import Q_always_true
from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.models import Submission, SubmissionReport
from oioioi.contests.utils import can_see_personal_data, is_contest_admin, is_contest_observer
from oioioi.oi.controllers import OIContestController
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.participants.utils import is_participant
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.szkopul.models import MAPCourseRegistration


class MAPCourse2024RegistrationController(ParticipantsController):
    registration_template = "map/registration.html"

    @property
    def form_class(self):
        from oioioi.szkopul.forms import MAPCourseRegistrationForm
        return MAPCourseRegistrationForm

    @property
    def participant_admin(self):
        from oioioi.szkopul.admin import MAPCourseRegistrationParticipantAdmin

        return MAPCourseRegistrationParticipantAdmin

    @classmethod
    def anonymous_can_enter_contest(cls):
        return True

    # Redundant because of filter_visible_contests, but saves a db query
    def can_enter_contest(self, request):
        return True

    def visible_contests_query(self, request):
        return Q_always_true()

    def can_register(self, request):
        return super().is_registration_open(request)

    def can_unregister(self, request, participant):
        return False

    def registration_view(self, request):
        participant = self._get_participant_for_form(request)

        if 'szkopul_mapcourseregistrationformdata' in request.session:
            # pylint: disable=not-callable
            form = self.form_class(request.session['szkopul_mapcourseregistrationformdata'])
            del request.session['szkopul_mapcourseregistrationformdata']
        else:
            form = self.get_form(request, participant)

        if request.method == 'POST':
            if '_add_school' in request.POST:
                data = request.POST.copy()
                data.pop('_add_school', None)
                data.pop('csrfmiddlewaretoken', None)
                request.session['szkopul_mapcourseregistrationformdata'] = data
                return redirect('add_school')
            elif form.is_valid():  # pylint: disable=maybe-no-member
                participant, created = Participant.objects.get_or_create(
                    contest=self.contest, user=request.user
                )

                self.handle_validated_form(request, form, participant)
                if 'next' in request.GET:
                    return safe_redirect(request, request.GET['next'])
                else:
                    return redirect('default_contest_view', contest_id=self.contest.id)

        context = {'form': form, 'participant': participant}
        return TemplateResponse(request, self.registration_template, context)

    def get_contest_participant_info_list(self, request, user):
        prev = super(MAPCourse2024RegistrationController, self).get_contest_participant_info_list(
            request, user
        )

        if can_see_personal_data(request):
            sensitive_info = MAPCourseRegistration.objects.filter(
                participant__user=user, participant__contest=request.contest
            )
            if sensitive_info.exists():
                context = {'model': sensitive_info[0]}
                rendered_sensitive_info = render_to_string(
                    'oi/sensitive_participant_info.html',
                    context=context,
                    request=request,
                )
                prev.append((2, rendered_sensitive_info))

        return prev

    def mixins_for_admin(self):
        from oioioi.participants.admin import TermsAcceptedPhraseAdminMixin

        return super(MAPCourse2024RegistrationController, self).mixins_for_admin() + (
            TermsAcceptedPhraseAdminMixin,
        )

    def can_change_terms_accepted_phrase(self, request):
        return not MAPCourseRegistration.objects.filter(
            participant__contest=request.contest
        ).exists()


class MAPCourse2024ContestController(ProgrammingContestController):
    description = _("MAP Course 2024 Contest")
    create_forum = True

    def registration_controller(self):
        return MAPCourse2024RegistrationController(self.contest)

    def can_submit(self, request, problem_instance, check_round_times = True):
        if request.user.is_anonymous:
            return False
        if request.user.has_perm('contests.contest_admin', self.contest):
            return True
        if not is_participant(request):
            return False
        return super(MAPCourse2024ContestController, self).can_submit(
            request, problem_instance, check_round_times
        )

    def can_see_stats(self, request):
        return is_contest_admin(request) or is_contest_observer(request)

    def should_confirm_submission_receipt(self, request, submission):
        return submission.kind == 'NORMAL' and request.user == submission.user

    def update_user_result_for_problem(self, result):
        try:
            latest_submission = (
                Submission.objects.filter(problem_instance=result.problem_instance)
                .filter(user=result.user)
                .filter(score__isnull=False)
                .exclude(status='CE')
                .filter(kind='NORMAL')
                .latest()
            )
            try:
                report = SubmissionReport.objects.get(
                    submission=latest_submission, status='ACTIVE', kind='NORMAL'
                )
            except SubmissionReport.DoesNotExist:
                report = None
            result.score = latest_submission.score
            result.status = latest_submission.status
            result.submission_report = report
        except Submission.DoesNotExist:
            result.score = None
            result.status = None
            result.submission_report = None

    def default_can_see_ranking(self, request):
        return is_contest_admin(request) or is_contest_observer(request)
