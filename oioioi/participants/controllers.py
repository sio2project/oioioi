from django import forms
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from django.http import HttpResponseRedirect
from oioioi.contests.controllers import RegistrationController
from oioioi.participants.models import Participant, RegistrationModel
import urllib

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
        if request.user.has_perm('contests.contest_admin', request.contest):
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
        assert self.form_class, 'ParticipantsController.form_class must ' \
                    'be overridden in subclasses'
        assert issubclass(self.form_class, forms.ModelForm), \
            'ParticipantsController.form_class must be a ModelForm'
        model_class = self.form_class._meta.model
        assert issubclass(model_class, RegistrationModel), \
            'ParticipantsController.form_class\'s model must be a ' \
            'subclass of RegistrationModel'
        return model_class

    def get_form(self, request, participant=None):
        model_class = self.get_model_class()
        instance = None
        if participant:
            try:
                instance = model_class.objects.get(participant=participant)
            except model_class.DoesNotExist:
                pass
        if request.method == 'POST':
            return self.form_class(request.POST, instance=instance)
        else:
            return self.form_class(instance=instance)

    def handle_validated_form(self, request, form, participant):
        instance = form.save(commit=False)
        instance.participant = participant
        instance.save()

    def registration_view(self, request):
        if not self.can_register(request):
            raise PermissionDenied
        try:
            participant = Participant.objects.get(contest=self.contest,
                    user=request.user)
        except Participant.DoesNotExist:
            participant = None

        form = self.get_form(request, participant)
        if request.method == 'POST':
            if form.is_valid():
                participant, created = Participant.objects.get_or_create(
                        contest=self.contest, user=request.user)
                self.handle_validated_form(request, form, participant)
                if 'next' in request.GET:
                    return HttpResponseRedirect(request.GET['next'])
                else:
                    return redirect('default_contest_view',
                            contest_id=self.contest)
        context = {'form': form, 'participant': participant}
        return TemplateResponse(request, self.registration_template, context)
