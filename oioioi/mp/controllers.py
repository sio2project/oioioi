import datetime
import logging
import unicodecsv

from django import forms
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _


from oioioi.base.utils.query_helpers import Q_always_true
from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.utils import (
    all_non_trial_public_results_visible,
    is_contest_admin,
    is_contest_observer,
)
from oioioi.filetracker.utils import make_content_disposition_header
from oioioi.mp.models import MPRegistration
# from oioioi.mp.score import PAScore
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.participants.utils import is_participant
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.rankings.controllers import DefaultRankingController


class MPRegistrationController(ParticipantsController):
    @property
    def form_class(self):
        from oioioi.mp.forms import MPRegistrationForm

        return MPRegistrationForm

    @property
    def participant_admin(self):
        from oioioi.mp.admin import MPRegistrationParticipantAdmin

        return MPRegistrationParticipantAdmin

    @classmethod
    def anonymous_can_enter_contest(self):
        return True

    def allow_login_as_public_name(self):
        return True

    # Redundant because of filter_visible_contests, but saves a db query
    def can_enter_contest(self, request):
        return True

    def visible_contests_query(self, request):
        return Q_always_true()

    def can_register(self, request):
        return True

    def can_unregister(self, request, participant):
        return False

    def registration_view(self, request):
        participant = self._get_participant_for_form(request)

        if 'mp_paregistrationformdata' in request.session:
            # pylint: disable=not-callable
            form = self.form_class(request.session['mp_paregistrationformdata'])
            del request.session['mp_paregistrationformdata']
        else:
            form = self.get_form(request, participant)
        form.set_terms_accepted_text(self.get_terms_accepted_phrase())

        if request.method == 'POST':
            # pylint: disable=maybe-no-member
            if form.is_valid():
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

    def mixins_for_admin(self):
        from oioioi.participants.admin import TermsAcceptedPhraseAdminMixin

        return super(MPRegistrationController, self).mixins_for_admin() + (
            TermsAcceptedPhraseAdminMixin,
        )

    def can_change_terms_accepted_phrase(self, request):
        return not MPRegistration.objects.filter(
            participant__contest=request.contest
        ).exists()


class MPContestController(ProgrammingContestController):
    description = _("Mistrz Programowania")
    create_forum = False

    # def update_user_result_for_problem(self, result):
    #     super(MPContestController, self).update_user_result_for_problem(result)
    #     if result.score is not None:
    #         result.score = MPScore(result.score)

    def registration_controller(self):
        return MPRegistrationController(self.contest)

    def ranking_controller(self):
        return MPRankingController(self.contest)

    def separate_public_results(self):
        return True

    def can_submit(self, request, problem_instance, check_round_times=True):
        if request.user.is_anonymous:
            return False
        if request.user.has_perm('contests.contest_admin', self.contest):
            return True
        if not is_participant(request):
            return False
        return super(MPContestController, self).can_submit(
            request, problem_instance, check_round_times
        )


class MPRankingController(DefaultRankingController):
    """
    """

    description = _("MP style ranking")

    # def _render_ranking_page(self, key, data, page):
    #     request = self._fake_request(page)
    #     data['is_admin'] = self.is_admin_key(key)
    #     return render_to_string(
    #         'mp/default_ranking.html', context=data, request=request
    #     )

    def _get_csv_header(self, key, data):
        header = [_("No."), _("Login"), _("First name"), _("Last name"), _("Sum")]
        for pi, _statement_visible in data['problem_instances']:
            header.append(pi.get_short_name_display())
        return header

    def _get_csv_row(self, key, row):
        line = [
            row['place'],
            row['user'].username,
            row['user'].first_name,
            row['user'].last_name,
            row['sum'],
        ]
        line += [r.score if r and r.score is not None else '' for r in row['results']]
        return line

    def render_ranking_to_csv(self, request, partial_key):
        key = self.get_full_key(request, partial_key)
        data = self.serialize_ranking(key)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = make_content_disposition_header(
            'attachment', u'%s-%s-%s.csv' % (_("ranking"), self.contest.id, key)
        )
        writer = unicodecsv.writer(response)

        writer.writerow(list(map(force_str, self._get_csv_header(key, data))))
        for row in data['rows']:
            writer.writerow(list(map(force_str, self._get_csv_row(key, row))))

        return response
