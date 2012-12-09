from django.contrib.admin.util import unquote
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelForm, ValidationError
from oioioi.base import admin
from oioioi.participants.models import Participant

def has_participants(request):
    rcontroller = request.contest.controller.registration_controller()
    return hasattr(rcontroller, 'participant_admin')

class ParticipantForm(ModelForm):
    class Meta:
        model = Participant

    def clean_user(self):
        if self.request_contest and Participant.objects.filter(
                contest=self.request_contest, user=self.cleaned_data['user']) \
                .exists():
            raise ValidationError(
                    _("%s is already a participant of this contest.")
                    % self.cleaned_data['user'].username)
        return self.cleaned_data['user']

class ParticipantAdmin(admin.ModelAdmin):
    list_select_related = True
    list_display = ['user_login', 'user_full_name', 'status']
    list_display_links = ['status']
    list_filter = ['status', ]
    fields = [('user', 'status'),]
    search_fields = ['user__username', 'user__last_name']
    actions = ['make_active', 'make_banned', 'delete_selected']
    form = ParticipantForm

    def user_login(self, instance):
        if not instance.user:
            return ''
        return instance.user.username
    user_login.short_description = _("Login")
    user_login.admin_order_field = 'user__username'

    def user_full_name(self, instance):
        if not instance.user:
            return ''
        return instance.user.get_full_name()
    user_full_name.short_description = _("User name")
    user_full_name.admin_order_field = 'user__last_name'

    def queryset(self, request):
        qs = super(ParticipantAdmin, self).queryset(request)
        qs = qs.filter(contest=request.contest)
        return qs

    def save_model(self, request, obj, form, change):
        obj.contest = request.contest
        obj.save()

    def get_form(self, request, obj=None, **kwargs):
        Form = super(ParticipantAdmin, self).get_form(request, obj, **kwargs)
        def form_wrapper(*args, **kwargs):
            form = Form(*args, **kwargs)
            form.request_contest = request.contest
            return form
        return form_wrapper

    def make_active(self, request, queryset):
        queryset.update(status='ACTIVE')
    make_active.short_description = _("Mark selected participants as active")

    def make_banned(self, request, queryset):
        queryset.update(status='BANNED')
    make_banned.short_description = _("Mark selected participants as banned")

class ContestDependentParticipantAdmin(admin.InstanceDependentAdmin):
    default_participant_admin = ParticipantAdmin

    def _find_model_admin(self, request, object_id):
        rcontroller = request.contest.controller.registration_controller()
        if hasattr(rcontroller, 'participant_admin'):
            participant_admin = rcontroller.participant_admin(self.model,
                                                              self.admin_site)
        else:
            participant_admin = self.default_participant_admin(self.model,
                                                               self.admin_site)
        return participant_admin

admin.site.register(Participant, ContestDependentParticipantAdmin)
admin.contest_admin_menu_registry.register('participants',
    _("Participants"),
    lambda request: reverse('oioioiadmin:participants_participant_changelist'),
    condition=has_participants, order=30)
