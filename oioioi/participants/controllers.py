import urllib

from django import forms
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.template.response import TemplateResponse
from django.http import HttpResponseRedirect

from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.controllers import RegistrationController
from oioioi.contests.utils import is_contest_admin
from oioioi.participants.models import Participant, RegistrationModel


class ParticipantsController(RegistrationController):
    registration_template = 'participants/registration.html'

    @property
    def form_class(self):
        return None

    @property
    def participant_admin(self):
        from oioioi.participants.admin import ParticipantAdmin
        return ParticipantAdmin

    def anonymous_can_enter_contest(self):
        return False

    def filter_participants(self, queryset):
        return queryset.filter(participant__contest=self.contest,
                participant__status='ACTIVE')

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

    def no_entry_view(self, request):
        if self.can_register(request):
            url = reverse('participants_register',
                        kwargs={'contest_id': self.contest.id}) + '?' + \
                    urllib.urlencode({'next': request.build_absolute_uri()})
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
        assert issubclass(self.form_class, forms.ModelForm), \
            'ParticipantsController.form_class must be a ModelForm'
        model_class = self.form_class._meta.model
        assert issubclass(model_class, RegistrationModel), \
            'ParticipantsController.form_class\'s model must be a ' \
            'subclass of RegistrationModel'
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
        if request.method == 'POST':
            return self.form_class(request.POST, instance=instance)
        else:
            return self.form_class(instance=instance)

    def handle_validated_form(self, request, form, participant):
        instance = form.save(commit=False)
        instance.participant = participant
        instance.save()

    def _get_participant_for_form(self, request):
        try:
            participant = Participant.objects.get(contest=self.contest,
                    user=request.user)
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
        assert form is not None, "can_register or can_edit_registration " \
            "returned True, but controller returns no registration form"

        if request.method == 'POST':
            if form.is_valid():
                participant, created = Participant.objects.get_or_create(
                        contest=self.contest, user=request.user)
                self.handle_validated_form(request, form, participant)
                if 'next' in request.GET:
                    return safe_redirect(request, request.GET['next'])
                else:
                    return redirect('default_contest_view',
                            contest_id=self.contest.id)
        context = {'form': form, 'participant': participant}
        return TemplateResponse(request, self.registration_template, context)
