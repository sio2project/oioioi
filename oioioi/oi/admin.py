import urllib.parse

from django.contrib import messages
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.base.utils import make_html_link
from oioioi.contests.admin import ContestAdmin
from oioioi.contests.models import Contest
from oioioi.contests.utils import administered_contests, get_inline_for_contest, is_contest_admin
from oioioi.oi.controllers import OIFinalOnsiteContestController
from oioioi.oi.forms import OIRegistrationForm
from oioioi.oi.models import OIDataConfirmation, OIDataConfirmationSettings, OIRegistration, School
from oioioi.participants.admin import OnsiteRegistrationParticipantAdmin, ParticipantAdmin


class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "participants_link",
        "address",
        "postal_code_link",
        "city",
        "province",
        "phone",
        "email",
        "is_active",
        "is_approved",
        "similar_schools",
    )
    list_filter = ("province", "city", "is_approved", "is_active")
    search_fields = ("name", "address", "postal_code")
    actions = (
        "make_active",
        "make_inactive",
        "approve",
        "disapprove",
        "merge_action",
        "delete_selected",
    )

    def get_list_display(self, request):
        if request.contest is None:
            return tuple(ld for ld in self.list_display if ld != "participants_link")
        return self.list_display

    def participants_link(self, instance):
        return make_html_link(instance.get_participants_url(), _("Participants"))

    participants_link.short_description = _("Participants")

    def postal_code_link(self, instance):
        url = reverse("oioioiadmin:oi_school_changelist") + "?" + urllib.parse.urlencode({"q": instance.postal_code})
        return make_html_link(url, instance.postal_code)

    postal_code_link.short_description = _("Postal code")
    postal_code_link.admin_order_field = "postal_code"

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

    disapprove.short_description = _("Mark selected schools as unapproved")

    def merge_action(self, request, queryset):
        approved = queryset.filter(is_approved=True)
        toMerge = queryset.filter(is_approved=False)
        if len(approved) != 1 or not toMerge:
            messages.error(
                request,
                _("You must select exactly one approved and at least one unapproved school."),
            )
            return None
        approved = approved[0]

        # https://docs.djangoproject.com/en/1.9/ref/models/meta/#migrating-old-meta-api
        def get_all_related_objects(modelObj):
            return [f for f in modelObj._meta.get_fields() if (f.one_to_many or f.one_to_one) and f.auto_created]

        # http://stackoverflow.com/questions/3393378/django-merging-objects
        related = get_all_related_objects(approved)
        valnames = {}
        for r in related:
            valnames.setdefault(r.related_model, []).append(r.field.name)

        for s in toMerge:
            for model, field_names in valnames.items():
                for field_name in field_names:
                    model.objects.filter(**{field_name: s}).update(**{field_name: approved})
            s.delete()

    merge_action.short_description = _("Merge all selected, unapproved schools into the approved one")


admin.site.register(School, SchoolAdmin)
admin.system_admin_menu_registry.register(
    "schools",
    _("Schools"),
    lambda request: reverse("oioioiadmin:oi_school_changelist"),
    order=20,
)


class OIRegistrationInline(admin.StackedInline):
    model = OIRegistration
    fk_name = "participant"
    form = OIRegistrationForm
    can_delete = False
    inline_classes = ("collapse open",)
    exclude = ("terms_accepted",)


class OIDataConfirmationInline(admin.StackedInline):
    model = OIDataConfirmation
    fk_name = "participant"
    can_delete = False
    inline_classes = ("collapse open",)


class OIRegistrationParticipantAdmin(ParticipantAdmin):
    list_display = ParticipantAdmin.list_display + [
        "school_name",
        "school_city",
        "school_province",
    ]
    inlines = tuple(ParticipantAdmin.inlines) + (OIRegistrationInline, OIDataConfirmationInline)
    readonly_fields = ["user"]
    search_fields = ParticipantAdmin.search_fields + [
        "oi_oiregistration__school__name",
        "oi_oiregistration__school__city",
        "oi_oiregistration__school__postal_code",
    ]

    list_filter = ParticipantAdmin.list_filter + ["oi_oiregistration__school__province"]

    def get_custom_list_select_related(self):
        return super().get_custom_list_select_related() + [
            "oi_oiregistration",
            "oi_oiregistration__school",
        ]

    def school_name(self, instance):
        if instance.oi_oiregistration.school is None:
            return _("-- school deleted --")
        return instance.oi_oiregistration.school.name

    school_name.short_description = _("School")
    school_name.admin_order_field = "oi_oiregistration__school__name"

    def school_city(self, instance):
        if instance.oi_oiregistration.school is None:
            return ""
        return instance.oi_oiregistration.school.city

    school_city.admin_order_field = "oi_oiregistration__school__city"

    def school_province(self, instance):
        if instance.oi_oiregistration.school is None:
            return ""
        return instance.oi_oiregistration.school.province

    school_province.admin_order_field = "oi_oiregistration__school__province"

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions


class OIFinalOnsiteParticipantAdmin(OnsiteRegistrationParticipantAdmin):
    list_display = OnsiteRegistrationParticipantAdmin.list_display + ["data_confirmed_at"]

    def get_custom_list_select_related(self):
        return super().get_custom_list_select_related() + ["oi_data_confirmation"]

    def data_confirmed_at(self, instance):
        return instance.oi_data_confirmation.data_confirmed_at

    data_confirmed_at.short_description = _("Data confirmed at")
    data_confirmed_at.admin_order_field = "oi_data_confirmation__data_confirmed_at"


class OIDataConfirmationSettingsInline(admin.StackedInline):
    model = OIDataConfirmationSettings
    fk_name = "contest"
    can_delete = False
    max_num = 1
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_admin(request)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        source_contest = formset.form.base_fields.get("source_contest")
        if source_contest is not None and obj is not None:
            # Keep a value set by someone who administers more contests than this user.
            current = OIDataConfirmationSettings.objects.filter(contest=obj).values("source_contest")
            source_contest.queryset = Contest.objects.filter(Q(id__in=[c.id for c in administered_contests(request)]) | Q(id__in=current))
        return formset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "source_contest" and isinstance(formfield.widget, RelatedFieldWidgetWrapper):
            formfield.widget = formfield.widget.widget
        return formfield


class OIDataConfirmationSettingsAdminMixin:
    """Adds :class:`~oioioi.oi.models.OIDataConfirmationSettings` to an admin
    panel when contest controller is OIFinalOnsiteContestController.
    """

    def get_inlines(self, request, obj):
        inlines = super().get_inlines(request, obj)
        if hasattr(obj, "controller") and isinstance(obj.controller, OIFinalOnsiteContestController):
            return inlines + [get_inline_for_contest(OIDataConfirmationSettingsInline, obj)]
        return inlines


ContestAdmin.mix_in(OIDataConfirmationSettingsAdminMixin)
