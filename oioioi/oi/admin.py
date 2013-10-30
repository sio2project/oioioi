import urllib

from django.contrib import messages
from django.contrib.admin import RelatedFieldListFilter
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base import admin
from oioioi.base.utils import make_html_link
from oioioi.base.permissions import make_request_condition
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.utils import is_contest_admin
from oioioi.participants.admin import ParticipantAdmin
from oioioi.oi.models import Region, School, OIRegistration, \
                                OIOnsiteRegistration
from oioioi.oi.forms import OIRegistrationForm, RegionForm
from oioioi.participants.utils import is_contest_with_participants


@make_request_condition
def is_onsite_contest(request):
    rcontroller = request.contest.controller.registration_controller()
    return is_contest_with_participants(request.contest) \
        and issubclass(rcontroller.participant_admin,
            OIOnsiteRegistrationParticipantAdmin)


class RegionAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'name')
    fields = ['short_name', 'name']
    form = RegionForm

    def has_add_permission(self, request):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def queryset(self, request):
        qs = super(RegionAdmin, self).queryset(request)
        qs = qs.filter(contest=request.contest)
        return qs

    def save_model(self, request, obj, form, change):
        obj.contest = request.contest
        obj.save()

    def get_form(self, request, obj=None, **kwargs):
        Form = super(RegionAdmin, self).get_form(request, obj, **kwargs)

        def form_wrapper(*args, **kwargs):
            form = Form(*args, **kwargs)
            form.request_contest = request.contest
            return form
        return form_wrapper

admin.site.register(Region, RegionAdmin)
contest_admin_menu_registry.register('regions', _("Regions"),
    lambda request: reverse('oioioiadmin:oi_region_changelist'),
    condition=is_onsite_contest, order=21)


class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'participants_link',
                    'address', 'postal_code_link', 'city', 'province',
                    'phone', 'email', 'is_active', 'is_approved',
                    'similar_schools')
    list_filter = ('province', 'city', 'is_approved', 'is_active')
    search_fields = ('name', 'address', 'postal_code')
    actions = ['make_active', 'make_inactive', 'approve', 'disapprove',
               'merge_action', 'delete_selected']

    def participants_link(self, instance):
        return make_html_link(instance.get_participants_url(),
                              _("Participants"))
    participants_link.allow_tags = True
    participants_link.short_description = _("Participants")

    def postal_code_link(self, instance):
        url = reverse('oioioiadmin:oi_school_changelist') + '?' + \
                urllib.urlencode({'q': instance.postal_code})
        return make_html_link(url, instance.postal_code)
    postal_code_link.allow_tags = True
    postal_code_link.short_description = _("Postal code")
    postal_code_link.admin_order_field = 'postal_code'

    def similar_schools(self, instance):
        schools = School.objects.filter(postal_code=instance.postal_code)
        return len([s for s in schools if instance.is_similar(s)]) - 1
    similar_schools.short_description = _("Similar schools")

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    make_active.short_description = _("Mark selected schools as active")

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    make_inactive.short_description = _("Mark selected schools as inactive")

    def approve(self, request, queryset):
        queryset.update(is_approved=True)
    approve.short_description = _("Mark selected schools as approved")

    def disapprove(self, request, queryset):
        queryset.update(is_approved=False)
    disapprove.short_description = _("Mark selected schools as disapproved")

    def merge_action(self, request, queryset):
        approved = queryset.filter(is_approved=True)
        toMerge = queryset.filter(is_approved=False)
        if len(approved) != 1 or not toMerge:
            messages.error(request, _("You shall select exactly one approved"
                     " school and at least one not approved."))
            return None
        approved = approved[0]

        # http://stackoverflow.com/questions/3393378/django-merging-objects
        related = approved._meta.get_all_related_objects()

        valnames = dict()
        for r in related:
            valnames.setdefault(r.model, []).append(r.field.name)

        for s in toMerge:
            for model, field_names in valnames.iteritems():
                for field_name in field_names:
                    model.objects.filter(**{field_name: s}) \
                            .update(**{field_name: approved})
            s.delete()
    merge_action.short_description = _("Merge all selected, not approved"
                                       " schools into approved one")

admin.site.register(School, SchoolAdmin)
admin.system_admin_menu_registry.register('schools',
    _("Schools"), lambda request:
    reverse('oioioiadmin:oi_school_changelist'), order=20)


class OIRegistrationInline(admin.StackedInline):
    model = OIRegistration
    fk_name = 'participant'
    form = OIRegistrationForm
    can_delete = False
    inline_classes = ('collapse open',)


class OIRegistrationParticipantAdmin(ParticipantAdmin):
    list_display = ParticipantAdmin.list_display \
            + ['school_name', 'school_city', 'school_province']
    inlines = ParticipantAdmin.inlines + [OIRegistrationInline, ]
    readonly_fields = ['user']
    search_fields = ParticipantAdmin.search_fields \
            + ['oi_oiregistration__school__name',
               'oi_oiregistration__school__city',
               'oi_oiregistration__school__postal_code']

    list_filter = ParticipantAdmin.list_filter \
            + ['oi_oiregistration__school__province']

    def get_list_select_related(self):
        return super(OIRegistrationParticipantAdmin, self) \
                .get_list_select_related() + ['oi_oiregistration',
                                              'oi_oiregistration__school']

    def school_name(self, instance):
        if instance.oi_oiregistration.school is None:
            return _("-- school deleted --")
        return instance.oi_oiregistration.school.name
    school_name.short_description = _("School")
    school_name.admin_order_field = 'oi_oiregistration__school__name'

    def school_city(self, instance):
        if instance.oi_oiregistration.school is None:
            return ''
        return instance.oi_oiregistration.school.city
    school_city.admin_order_field = 'oi_oiregistration__school__city'

    def school_province(self, instance):
        if instance.oi_oiregistration.school is None:
            return ''
        return instance.oi_oiregistration.school.province
    school_province.admin_order_field = 'oi_oiregistration__school__province'

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_actions(self, request):
        actions = super(OIRegistrationParticipantAdmin, self) \
                .get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class OIOnsiteRegistrationInline(admin.TabularInline):
    model = OIOnsiteRegistration
    fk_name = 'participant'
    can_delete = False

    def has_add_permission(self, request):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)


class RegionFilter(RelatedFieldListFilter):
    def __init__(self, field, request, *args, **kwargs):
        super(RegionFilter, self).__init__(field, request, *args, **kwargs)
        contest = request.contest
        self.lookup_choices = [(r.id, unicode(r))
                               for r in contest.region_set.all()]


class OIOnsiteRegistrationParticipantAdmin(ParticipantAdmin):
    list_display = ParticipantAdmin.list_display \
            + ['number', 'region', 'local_number']
    inlines = ParticipantAdmin.inlines + [OIOnsiteRegistrationInline]
    list_filter = ParticipantAdmin.list_filter \
            + [('oi_oionsiteregistration__region', RegionFilter)]
    ordering = ['oi_oionsiteregistration__number']
    search_fields = ParticipantAdmin.search_fields \
            + ['oi_oionsiteregistration__number']

    def get_list_select_related(self):
        return super(OIOnsiteRegistrationParticipantAdmin, self) \
                .get_list_select_related() + \
                ['oi_oionsiteregistration', 'oi_oionsiteregistration__region']

    def number(self, instance):
        return instance.oi_oionsiteregistration.number
    number.admin_order_field = 'oi_oionsiteregistration__number'

    def region(self, instance):
        return instance.oi_oionsiteregistration.region
    region.admin_order_field = 'oi_oionsiteregistration__region'

    def local_number(self, instance):
        return instance.oi_oionsiteregistration.local_number
    local_number.admin_order_field = 'oi_oionsiteregistration__local_number'
