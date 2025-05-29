import logging
import urllib.parse
from django import forms
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils import get_user_display_name, request_cached
from oioioi.base.utils.query_helpers import Q_always_true
from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.controllers import ContestController, RegistrationController
from oioioi.contests.models import RegistrationAvailabilityConfig
from oioioi.contests.utils import can_see_personal_data, is_contest_admin, is_contest_archived
from oioioi.participants.models import (
    OnsiteRegistration,
    Participant,
    RegistrationModel,
    TermsAcceptedPhrase,
)
from oioioi.contests.models import RegistrationStatus

auditLogger = logging.getLogger(__name__ + ".audit")

class ParticipantsController(RegistrationController):
    registration_template = 'participants/registration.html'

    @property
    def form_class(self):
        return None

    @property
    def participant_admin(self):
        from oioioi.participants.admin import ParticipantAdmin

        return ParticipantAdmin

    @classmethod
    def anonymous_can_enter_contest(cls):
        return False

    def allow_login_as_public_name(self):
        """Determines if participants may choose to stay anonymous,
        i.e. use their logins as public names.
        """
        return False

    def filter_participants(self, queryset):
        return queryset.filter(
            participant__contest=self.contest, participant__status='ACTIVE'
        )

    def user_contests_query(self, request):
        if not request.user.is_authenticated:
            return Q(pk__isnull=True) # (False)
        return Q(participant__user__id=request.user.id, participant__status='ACTIVE')

    def filter_users_with_accessible_personal_data(self, queryset):
        return self.filter_participants(queryset)

    def can_register(self, request):
        return False

    def can_edit_registration(self, request, participant):
        if self.form_class is None:
            return False
        if is_contest_admin(request):
            return True
        if participant.status == 'BANNED':
            return False
        return bool(request.user == participant.user)

    def can_unregister(self, request, participant):
        return self.can_edit_registration(request, participant)

    def no_entry_view(self, request):
        if self.can_register(request):
            url = (
                reverse('participants_register', kwargs={'contest_id': self.contest.id})
                + '?'
                + urllib.parse.urlencode(
                    {'next': request.build_absolute_uri()}
                )
            )
            return HttpResponseRedirect(url)
        return super(ParticipantsController, self).no_entry_view(request)

    def get_model_class(self):
        """Returns registration model class used within current registration
        controller.

        The default implementation infers it from form_class form metadata.
        If there is no form_class, the default implementation returns
        ``None``.
        """
        if self.form_class is None:
            return None
        assert issubclass(
            self.form_class, forms.ModelForm
        ), 'ParticipantsController.form_class must be a ModelForm'
        model_class = self.form_class._meta.model
        assert issubclass(model_class, RegistrationModel), (
            'ParticipantsController.form_class\'s model must be a '
            'subclass of RegistrationModel'
        )
        return model_class

    def get_form(self, request, participant=None):
        if self.form_class is None:
            return None
        instance = None
        if participant:
            try:
                instance = participant.registration_model
            except ObjectDoesNotExist:
                pass
        # pylint: disable=not-callable
        if request.method == 'POST':
            form = self.form_class(request.POST, request.FILES, instance=instance)
        else:
            form = self.form_class(instance=instance)

        if self.allow_login_as_public_name():
            initial = participant.anonymous if participant else False
            form.fields['anonymous'] = forms.BooleanField(
                required=False,
                label=_("Anonymous"),
                initial=initial,
                help_text=_(
                    "Anonymous participant uses the account name "
                    "instead of the real name in rankings."
                ),
            )
        return form

    def handle_validated_form(self, request, form, participant):
        instance = form.save(commit=False)
        instance.participant = participant
        instance.save()
        participant.anonymous = form.cleaned_data.get('anonymous', False)
        participant.save()

    def _get_participant_for_form(self, request):
        try:
            participant = Participant.objects.get(
                contest=self.contest, user=request.user
            )
            if not self.can_edit_registration(request, participant):
                raise PermissionDenied
        except Participant.DoesNotExist:
            participant = None
        if participant is None and not self.can_register(request):
            raise PermissionDenied
        return participant

    def registration_view(self, request):
        participant = self._get_participant_for_form(request)

        form = self.get_form(request, participant)
        assert form is not None, (
            "can_register or can_edit_registration "
            "returned True, but controller returns no registration form"
        )

        if request.method == 'POST':
            if form.is_valid():
                participant, created = Participant.objects.get_or_create(
                    contest=self.contest, user=request.user
                )
                self.handle_validated_form(request, form, participant)
                if 'next' in request.GET:
                    return safe_redirect(request, request.GET['next'])
                else:
                    return redirect('default_contest_view', contest_id=self.contest.id)
        can_unregister = False
        if participant:
            can_unregister = self.can_unregister(request, participant)
        context = {
            'form': form,
            'participant': participant,
            'can_unregister': can_unregister,
        }
        return TemplateResponse(request, self.registration_template, context)

    def get_terms_accepted_phrase(self):
        try:
            return self.contest.terms_accepted_phrase
        except TermsAcceptedPhrase.DoesNotExist:
            return None

    def can_change_terms_accepted_phrase(self, request):
        """
        :return: Whether the given contest has custom registered
        participants (like the ones in OI and PA).
        Then and only then we allow to change terms accepted phrase.
        """
        return True

    def is_registration_open(self, request):
        if is_contest_archived(request):
            return False
        try:
            rvc = RegistrationAvailabilityConfig.objects.get(contest=request.contest)
            return rvc.is_registration_open(request.timestamp)
        except RegistrationAvailabilityConfig.DoesNotExist:
            auditLogger.warning("RegistrationAvailabilityConfig does not exist for contest %s", request.contest)
            return True

    def registration_status(self, request):
        if is_contest_archived(request):
            return RegistrationStatus.CLOSED
        try:
            rvc = RegistrationAvailabilityConfig.objects.get(contest=request.contest)
            return rvc.registration_status(request.timestamp)
        except RegistrationAvailabilityConfig.DoesNotExist:
            auditLogger.warning("RegistrationAvailabilityConfig does not exist for contest %s", request.contest)
            return RegistrationStatus.OPEN


class OpenParticipantsController(ParticipantsController):
    @property
    def form_class(self):
        from oioioi.participants.forms import OpenRegistrationForm

        return OpenRegistrationForm

    @classmethod
    def anonymous_can_enter_contest(cls):
        return True

    def allow_login_as_public_name(self):
        return True

    # Redundant because of filter_visible_contests, but saves a db query
    def can_enter_contest(self, request):
        return True

    def visible_contests_query(self, request):
        return Q_always_true()

    def can_register(self, request):
        if is_contest_archived(request):
            return False
        return True

    def can_unregister(self, request, participant):
        return False


@request_cached
def anonymous_participants(request):
    if not hasattr(request, 'contest'):
        return frozenset({})
    return frozenset(
        (
            p.user
            for p in Participant.objects.filter(
                contest=request.contest, anonymous=True
            ).select_related('user')
        )
    )


class EmailShowContestControllerMixin(object):
    """Contest controller defines whether in participants' data view email
    should be shown. That is a case in OI-type contest.
    """

    show_email_in_participants_data = False


ContestController.mix_in(EmailShowContestControllerMixin)


class AnonymousContestControllerMixin(object):
    """ContestController mixin that adds participants info for anonymous
    contests.
    """

    def get_user_public_name(self, request, user):
        assert self.contest == request.contest
        if (
            request.user.is_superuser
            or can_see_personal_data(request)
            or user not in anonymous_participants(request)
        ):
            return get_user_display_name(user)
        else:
            return user.username

    def get_contest_participant_info_list(self, request, user):
        prev = super(
            AnonymousContestControllerMixin, self
        ).get_contest_participant_info_list(request, user)
        try:
            part = Participant.objects.get(user=user, contest=request.contest)
            context = {'participant': part}
            rendered_info = render_to_string(
                'participants/participant_info.html', context=context, request=request
            )
            prev.append((98, rendered_info))
        except Participant.DoesNotExist:
            pass
        return prev


ContestController.mix_in(AnonymousContestControllerMixin)


class OnsiteRegistrationController(ParticipantsController):
    @property
    def participant_admin(self):
        from oioioi.participants.admin import OnsiteRegistrationParticipantAdmin

        return OnsiteRegistrationParticipantAdmin

    def get_model_class(self):
        return OnsiteRegistration

    def can_register(self, request):
        return False

    def can_edit_registration(self, request, participant):
        return False

    def get_contest_participant_info_list(self, request, user):
        prev = super(
            OnsiteRegistrationController, self
        ).get_contest_participant_info_list(request, user)

        info = OnsiteRegistration.objects.filter(
            participant__user=user, participant__contest=request.contest
        )

        if info.exists():
            context = {'model': info[0]}
            rendered_info = render_to_string(
                'oi/participant_info.html', context=context, request=request
            )
            prev.append((98, rendered_info))

        return prev


class OnsiteContestControllerMixin(object):
    """ContestController mixin that sets up an onsite contest."""

    create_forum = False

    def registration_controller(self):
        return OnsiteRegistrationController(self.contest)

    def should_confirm_submission_receipt(self, request, submission):
        return False

    def is_onsite(self):
        return True
