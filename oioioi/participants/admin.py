from django.contrib.admin import RelatedFieldListFilter, SimpleListFilter
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from oioioi.base import admin
from oioioi.base.utils import make_html_link
from oioioi.contests.admin import RoundTimeExtensionAdmin, SubmissionAdmin, contest_site
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import RoundTimeExtension
from oioioi.contests.utils import is_contest_admin
from oioioi.participants.forms import (
    ExtendRoundForm,
    ParticipantForm,
    RegionForm,
    TermsAcceptedPhraseForm,
)
from oioioi.participants.models import (
    OnsiteRegistration,
    Participant,
    Region,
    TermsAcceptedPhrase,
)
from oioioi.participants.utils import (
    contest_has_participants,
    contest_is_onsite,
    has_participants_admin,
)


class ParticipantAdmin(admin.ModelAdmin):
    list_select_related = True
    list_display = ['user_login', 'user_full_name', 'status']
    list_filter = [
        'status',
    ]
    fields = [
        ('user', 'status'),
    ]
    search_fields = ['user__username', 'user__last_name']
    actions = ('make_active', 'make_banned', 'delete_selected', 'extend_round')
    form = ParticipantForm

    def has_add_permission(self, request):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def user_login(self, instance):
        if not instance.user:
            return ''
        return instance.user.username

    user_login.short_description = _("Login")
    user_login.admin_order_field = 'user__username'

    def user_full_name(self, instance):
        if not instance.user:
            return ''
        return make_html_link(
            reverse(
                'user_info',
                kwargs={'contest_id': instance.contest.id, 'user_id': instance.user.id},
            ),
            instance.user.get_full_name(),
        )

    user_full_name.short_description = _("User name")
    user_full_name.admin_order_field = 'user__last_name'

    def get_custom_list_select_related(self):
        return super(ParticipantAdmin, self).get_custom_list_select_related() + [
            'contest',
            'user',
        ]

    def get_list_display(self, request):
        ld = super(ParticipantAdmin, self).get_list_display(request)
        rcontroller = request.contest.controller.registration_controller()
        if rcontroller.allow_login_as_public_name():
            return ld + ['anonymous']
        return ld

    def get_queryset(self, request):
        qs = super(ParticipantAdmin, self).get_queryset(request)
        qs = qs.filter(contest=request.contest)
        return qs

    def save_model(self, request, obj, form, change):
        obj.contest = request.contest
        obj.save()

    def get_form(self, request, obj=None, **kwargs):
        if not self.has_change_permission(request, obj):
            return super(ParticipantAdmin, self).get_form(request, obj, **kwargs)

        Form = super(ParticipantAdmin, self).get_form(request, obj, **kwargs)

        def form_wrapper(*args, **kwargs):
            form = Form(*args, **kwargs)
            form.request_contest = request.contest
            return form

        return form_wrapper

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = User.objects.all().order_by('username')
        return super(ParticipantAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

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
                existing_extensions = RoundTimeExtension.objects.filter(
                    round=round, user__in=users
                )
                for extension in existing_extensions:
                    extension.extra_time += extra_time
                    extension.save()
                existing_count = existing_extensions.count()

                new_extensions = [
                    RoundTimeExtension(user=user, round=round, extra_time=extra_time)
                    for user in users
                    if not existing_extensions.filter(user=user).exists()
                ]
                RoundTimeExtension.objects.bulk_create(new_extensions)

                if existing_count:
                    if existing_count > 1:
                        name = capfirst(RoundTimeExtension._meta.verbose_name_plural)
                    else:
                        name = RoundTimeExtension._meta.verbose_name
                    self.message_user(
                        request,
                        ngettext_lazy(
                            "Updated one %(name)s.",
                            "%(name)s updated: %(existing_count)d.",
                            existing_count,
                        )
                        % {'existing_count': existing_count, 'name': name},
                    )
                if new_extensions:
                    if len(new_extensions) > 1:
                        name = capfirst(RoundTimeExtension._meta.verbose_name_plural)
                    else:
                        name = RoundTimeExtension._meta.verbose_name
                    self.message_user(
                        request,
                        ngettext_lazy(
                            "Created one %(name)s.",
                            "%(name)s created: %(new_count)d.",
                            len(new_extensions),
                        )
                        % {'new_count': len(new_extensions), 'name': name},
                    )

                return HttpResponseRedirect(request.get_full_path())

        if not form:
            form = ExtendRoundForm(
                request.contest, initial={'_selected_action': [p.id for p in queryset]}
            )

        return TemplateResponse(
            request, 'admin/participants/extend_round.html', {'form': form}
        )

    extend_round.short_description = _("Extend round")


class NoParticipantAdmin(ParticipantAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ContestDependentParticipantAdmin(admin.InstanceDependentAdmin):
    default_participant_admin = NoParticipantAdmin

    def _find_model_admin(self, request, object_id):
        rcontroller = request.contest.controller.registration_controller()
        if has_participants_admin(request):
            participant_admin = rcontroller.participant_admin(
                self.model, self.admin_site
            )
        else:
            participant_admin = self.default_participant_admin(
                self.model, self.admin_site
            )
        return participant_admin

    def _model_admin_for_instance(self, request, instance=None):
        raise NotImplementedError


contest_site.contest_register(Participant, ContestDependentParticipantAdmin)
contest_admin_menu_registry.register(
    'participants',
    _("Participants"),
    lambda request: reverse('oioioiadmin:participants_participant_changelist'),
    condition=has_participants_admin,
    order=30,
)


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    readonly_fields = ('contest', 'status')

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # Protected by parent ModelAdmin
        return True

    def has_delete_permission(self, request, obj=None):
        return False


class RegionAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'name', 'region_server')
    fields = ['short_name', 'name', 'region_server']
    form = RegionForm

    def has_add_permission(self, request):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_queryset(self, request):
        qs = super(RegionAdmin, self).get_queryset(request)
        qs = qs.filter(contest=request.contest)
        return qs

    def save_model(self, request, obj, form, change):
        obj.contest = request.contest
        obj.save()

    def get_form(self, request, obj=None, **kwargs):
        if not self.has_change_permission(request, obj):
            return super(RegionAdmin, self).get_form(request, obj, **kwargs)

        Form = super(RegionAdmin, self).get_form(request, obj, **kwargs)

        def form_wrapper(*args, **kwargs):
            form = Form(*args, **kwargs)
            form.request_contest = request.contest
            return form

        return form_wrapper


contest_site.contest_register(Region, RegionAdmin)
contest_admin_menu_registry.register(
    'regions',
    _("Regions"),
    lambda request: reverse('oioioiadmin:participants_region_changelist'),
    condition=contest_is_onsite,
    order=21,
)


class OnsiteRegistrationInline(admin.TabularInline):
    model = OnsiteRegistration
    fk_name = 'participant'
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "region":
            kwargs["queryset"] = Region.objects.filter(contest=request.contest)
        return super(OnsiteRegistrationInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class RegionFilter(RelatedFieldListFilter):
    def __init__(self, field, request, *args, **kwargs):
        super(RegionFilter, self).__init__(field, request, *args, **kwargs)
        contest = request.contest
        self.lookup_choices = [(r.id, str(r)) for r in contest.regions.all()]


class OnsiteRegistrationParticipantAdmin(ParticipantAdmin):
    list_display = ParticipantAdmin.list_display + ['number', 'region', 'local_number']
    inlines = tuple(ParticipantAdmin.inlines) + (OnsiteRegistrationInline,)
    list_filter = ParticipantAdmin.list_filter + [
        ('participants_onsiteregistration__region', RegionFilter)
    ]
    ordering = ['participants_onsiteregistration__number']
    search_fields = ParticipantAdmin.search_fields + [
        'participants_onsiteregistration__number'
    ]

    def get_custom_list_select_related(self):
        return super(
            OnsiteRegistrationParticipantAdmin, self
        ).get_custom_list_select_related() + [
            'participants_onsiteregistration',
            'participants_onsiteregistration__region',
        ]

    def number(self, instance):
        return instance.participants_onsiteregistration.number

    number.admin_order_field = 'participants_onsiteregistration__number'

    def region(self, instance):
        return instance.participants_onsiteregistration.region

    region.admin_order_field = 'participants_onsiteregistration__region'

    def local_number(self, instance):
        return instance.participants_onsiteregistration.local_number

    local_number.admin_order_field = 'participants_onsiteregistration__local_number'


class RegionListFilter(SimpleListFilter):
    title = _("region")
    parameter_name = 'region'

    def lookups(self, request, model_admin):
        regions = Region.objects.filter(contest=request.contest)
        return [(x, x.name) for x in regions]

    def queryset(self, request, queryset):
        name = self.value()
        if name:
            kwargs = {
                'user__participant__contest': request.contest,
                'user__participant__participants_onsiteregistration__'
                'region__short_name': name,
            }
            return queryset.filter(**kwargs)
        else:
            return queryset


class OnsiteSubmissionAdminMixin(object):
    """Adds :class:`~oioioi.participants.admin.RegionListFilter` filter to
    an admin panel.
    """

    def __init__(self, *args, **kwargs):
        super(OnsiteSubmissionAdminMixin, self).__init__(*args, **kwargs)

    def get_list_filter(self, request):
        return super(OnsiteSubmissionAdminMixin, self).get_list_filter(request) + [
            RegionListFilter
        ]


SubmissionAdmin.mix_in(OnsiteSubmissionAdminMixin)


class UserWithParticipantsAdminMixin(object):
    """Adds :class:`~oioioi.participants.models.Participant` to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(UserWithParticipantsAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (ParticipantInline,)


admin.OioioiUserAdmin.mix_in(UserWithParticipantsAdminMixin)


class ParticipantsRoundTimeExtensionMixin(object):
    """Adds contest participants to an admin panel."""

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            if contest_has_participants(request):
                kwargs['queryset'] = User.objects.filter(
                    id__in=Participant.objects.filter(
                        contest=request.contest
                    ).values_list('user', flat=True)
                ).order_by('username')
        return super(
            ParticipantsRoundTimeExtensionMixin, self
        ).formfield_for_foreignkey(db_field, request, **kwargs)


RoundTimeExtensionAdmin.mix_in(ParticipantsRoundTimeExtensionMixin)


# Normally it would be better to use TabularInline,
# because we have at most one object of this type per contest.
# StackedInline was used instead,
# because help_text didn't want to work with tabular one.
# If you are reading this and know how to fix this, feel free to do it!
class TermsAcceptedPhraseInline(admin.StackedInline):
    model = TermsAcceptedPhrase
    can_delete = False
    form = TermsAcceptedPhraseForm
    max_num = 0
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return False

    # We don't want anyone (even admins) to be able to change terms accepted
    # phrase, if some participant has already registered.
    # This is because we cannot assume participants would accept the new one.
    def get_readonly_fields(self, request, obj=None):
        result = super(TermsAcceptedPhraseInline, self).get_readonly_fields(
            request, obj
        )

        if not is_contest_admin(
            request
        ) or not request.contest.controller.registration_controller().can_change_terms_accepted_phrase(
            request
        ):
            result = result + ('text',)

        return result


class TermsAcceptedPhraseAdminMixin(object):
    """Adds :class:`~oioioi.participants.models.TermsAcceptedPhrase` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(TermsAcceptedPhraseAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (TermsAcceptedPhraseInline,)
