from django.contrib.admin.util import unquote
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from oioioi.base import admin
from oioioi.participants.forms import ParticipantForm, ExtendRoundForm
from oioioi.participants.models import Participant
from oioioi.contests.models import RoundTimeExtension

def has_participants(request):
    rcontroller = request.contest.controller.registration_controller()
    return hasattr(rcontroller, 'participant_admin')

class ParticipantAdmin(admin.ModelAdmin):
    list_select_related = True
    list_display = ['user_login', 'user_full_name', 'status']
    list_filter = ['status', ]
    fields = [('user', 'status'),]
    search_fields = ['user__username', 'user__last_name']
    actions = ['make_active', 'make_banned', 'delete_selected', 'extend_round']
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

    def extend_round(self, request, queryset):
        form = None

        if 'submit' in request.POST:
            form = ExtendRoundForm(request.contest, request.POST)

            if form.is_valid():
                round = form.cleaned_data['round']
                extra_time = form.cleaned_data['extra_time']

                users = [participant.user for participant in queryset]
                existing_extensions = RoundTimeExtension.objects \
                        .filter(round=round, user__in=users)
                for extension in existing_extensions:
                    extension.extra_time += extra_time;
                    extension.save()
                existing_count = existing_extensions.count()

                new_extensions = [RoundTimeExtension(user=user, round=round,
                        extra_time=extra_time) for user in users \
                        if not existing_extensions.filter(user=user).exists()]
                RoundTimeExtension.objects.bulk_create(new_extensions)

                self.message_user(request, _("Created %(new_count)d and updated"
                    "%(updated_count)d %(name)s.")
                    % {'new_count': len(new_extensions),
                       'updated_count': existing_count,
                       'name': RoundTimeExtension._meta.verbose_name_plural.lower()})

                return HttpResponseRedirect(request.get_full_path())

        if not form:
            form = ExtendRoundForm(request.contest,
                    initial={'_selected_action': [p.id for p in queryset]})

        return TemplateResponse(request, 'admin/participants/extend_round.html',
                {'form': form})
    extend_round.short_description = _("Extend round")

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
